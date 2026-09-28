import io
import json
import os
import re
import time
from datetime import datetime, timezone
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

from providers import configured_providers
from storage import get_alert, initialize, list_saved_jobs, remove_saved_job, save_alert, save_job

app = FastAPI(title="Resufind API", version="0.1.0")
initialize()
allowed_origins = [origin.strip() for origin in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",") if origin.strip()]
app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
SKILL_CATALOG = ["Python", "TypeScript", "JavaScript", "React", "Next.js", "FastAPI", "SQL", "PostgreSQL", "Figma", "Product strategy", "User research", "Data analysis", "Machine learning", "AWS", "Docker", "Git", "Agile", "Communication"]

JOB_FIXTURES = [
    {"id": "northstar-product", "title": "Senior Product Designer", "company": "Northstar Labs", "location": "Remote · US", "salary": "$145k – $175k", "description": "Lead product design for a thoughtful collaboration platform. Partner with product and engineering across discovery, prototyping, and launch.", "apply_link": "https://example.com/jobs/northstar-product", "source": "Company careers", "posted_date": "2026-09-26", "job_type": "Full-time", "skills": ["Figma", "User research", "Product strategy"]},
    {"id": "orbit-data", "title": "Product Data Analyst", "company": "Orbit Systems", "location": "New York · Hybrid", "salary": "$115k – $138k", "description": "Turn product behavior into decisions with SQL, experimentation, and clear storytelling for a fast-moving product team.", "apply_link": "https://example.com/jobs/orbit-data", "source": "Wellfound", "posted_date": "2026-09-24", "job_type": "Full-time", "skills": ["SQL", "Data analysis", "Communication"]},
    {"id": "fieldnotes-fullstack", "title": "Full-stack Engineer", "company": "Field Notes", "location": "Remote · Worldwide", "salary": "$130k – $165k", "description": "Build elegant tools for independent teams using TypeScript, React, Python, and a pragmatic product mindset.", "apply_link": "https://example.com/jobs/fieldnotes-fullstack", "source": "RemoteOK", "posted_date": "2026-09-22", "job_type": "Full-time", "skills": ["TypeScript", "React", "Python"]},
    {"id": "commonthread-research", "title": "UX Researcher", "company": "Common Thread", "location": "London · Hybrid", "salary": "£70k – £88k", "description": "Plan and run qualitative research that helps a growing fintech make simpler, more human decisions.", "apply_link": "https://example.com/jobs/commonthread-research", "source": "Company careers", "posted_date": "2026-09-18", "job_type": "Contract", "skills": ["User research", "Communication", "Agile"]},
]

class SearchProfile(BaseModel):
    headline: str = ""
    years_experience: str = ""
    location: str = ""
    skills: list[str] = []
    work_mode: str = "Remote"
    job_type: str = "Full-time"
    expected_salary: str = ""
    industry: str = ""

class SavedJobRequest(BaseModel):
    user_id: str = "demo-user"
    job: dict

class AlertRequest(BaseModel):
    user_id: str = "demo-user"
    email: str
    cadence: str = "weekly"
    profile: SearchProfile

ROLE_ALIASES = {
    "ux": {"ux", "user experience", "ux designer", "product designer", "interaction designer", "ui/ux"},
    "product": {"product", "product designer", "product design"},
    "designer": {"designer", "design", "ux", "user experience"},
    "engineer": {"engineer", "developer", "software"},
    "analyst": {"analyst", "analytics", "data"},
    "researcher": {"researcher", "research", "ux research", "user research"},
}

LOCATION_TRANSLATIONS = {"الهند": "India", "المملكة المتحدة": "United Kingdom", "الولايات المتحدة": "United States"}

def normalized_location(value: str) -> str:
    result = value.strip()
    for localized, english in LOCATION_TRANSLATIONS.items():
        result = result.replace(localized, english)
    return result.lower()

def role_matches(profile: SearchProfile, job: dict) -> bool:
    requested = normalized_location(profile.headline)
    if not requested:
        return True
    job_title = normalized_location(job["title"])
    requested_words = [word for word in re.findall(r"[a-z0-9/]+", requested) if len(word) > 2]
    title_terms = set(re.findall(r"[a-z0-9/]+", job_title))
    for word in requested_words:
        aliases = ROLE_ALIASES.get(word, {word})
        if any(alias in job_title for alias in aliases) or word in title_terms:
            return True
    return False

def location_matches(profile: SearchProfile, job: dict) -> bool:
    requested = normalized_location(profile.location)
    job_location = normalized_location(job["location"])
    if requested and requested not in {"remote", "remote only", "work from home"} and requested not in job_location:
        return False
    mode = profile.work_mode.lower()
    if mode == "remote":
        return "remote" in job_location or not requested
    if mode == "hybrid":
        return "hybrid" in job_location
    if mode in {"on-site", "onsite", "on site"}:
        return "remote" not in job_location and "hybrid" not in job_location
    return True

def job_type_matches(profile: SearchProfile, job: dict) -> bool:
    requested = profile.job_type.lower().replace("-", "")
    actual = job["job_type"].lower().replace("-", "")
    if requested == "internship":
        return "intern" in actual or "intern" in job["title"].lower() or "intern" in job["description"].lower()
    return not requested or requested in actual

def score_job(profile: SearchProfile, job: dict) -> dict:
    requested_skills = {skill.lower() for skill in profile.skills}
    job_skills = {skill.lower() for skill in job["skills"]}
    skill_overlap = len(requested_skills & job_skills)
    skill_score = round((skill_overlap / max(len(requested_skills), 1)) * 45)
    category_score = 30 if role_matches(profile, job) else 0
    location_score = 15 if location_matches(profile, job) else 0
    type_score = 10 if job_type_matches(profile, job) else 0
    industry_score = 5 if not profile.industry or normalized_location(profile.industry) in normalized_location(f"{job['title']} {job['description']}") else 0
    score = min(99, skill_score + category_score + location_score + type_score + industry_score)
    reasons = []
    if skill_overlap: reasons.append(f"{skill_overlap} of your skills match")
    if category_score: reasons.append("role category aligns with your target")
    if "remote" in job["location"].lower(): reasons.append("remote-friendly location")
    if industry_score: reasons.append("industry preference is represented")
    return {**job, "match_score": score, "match_reasons": reasons or ["strong adjacent experience"]}

def extract_text(filename: str, content: bytes) -> str:
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "pdf":
        from pypdf import PdfReader
        return "\n".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    if extension == "docx":
        from docx import Document
        return "\n".join(paragraph.text for paragraph in Document(io.BytesIO(content)).paragraphs)
    raise HTTPException(status_code=415, detail="Please upload a PDF or DOCX resume.")

def parse_profile(text: str) -> dict:
    clean_text = re.sub(r"\s+", " ", text).strip()
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "")
    found_skills = [skill for skill in SKILL_CATALOG if re.search(rf"\b{re.escape(skill)}\b", clean_text, re.I)]
    years_match = re.search(r"(\d+)\+?\s+years?", clean_text, re.I)
    role_match = re.search(r"(?:currently|role|title|position)[:\s]+([^\n|]{3,60})", text, re.I)
    return {"name": first_line[:80], "headline": role_match.group(1).strip() if role_match else "", "years_experience": years_match.group(1) if years_match else "", "location": "", "skills": found_skills, "roles": [], "education": [], "summary": f"Profile signal created from {len(clean_text.split())} words. Review the highlighted details before searching."}

AI_INSTRUCTIONS = "Extract a job candidate profile from the resume. Return only JSON with string keys name, headline, years_experience, location, summary and array keys skills, roles, education. Do not invent missing facts."

def apply_ai_profile(profile: dict, candidate: dict) -> dict:
    for field in ("name", "headline", "years_experience", "location", "summary"):
        if isinstance(candidate.get(field), str) and candidate[field].strip():
            profile[field] = candidate[field].strip()
    for field in ("skills", "roles", "education"):
        if isinstance(candidate.get(field), list):
            profile[field] = [str(item).strip() for item in candidate[field] if str(item).strip()]
    return profile

def enrich_with_gemini(profile: dict, resume_text: str, api_key: str) -> tuple[dict, str]:
    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    if model in {"gemini-2.0-flash", "gemini-3.8-flash", "gemini-2.5-flash-lite"}:
        model = "gemini-flash-lite-latest"
    payload = {"contents": [{"parts": [{"text": f"{AI_INSTRUCTIONS}\n\nResume:\n{resume_text[:30000]}"}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
    for attempt in range(3):
        try:
            with urlopen(request, timeout=20) as response:
                content = json.loads(response.read().decode("utf-8"))["candidates"][0]["content"]["parts"][0]["text"]
            return apply_ai_profile(profile, json.loads(content)), "gemini"
        except HTTPError as error:
            if error.code not in {429, 503} or attempt == 2:
                raise
            time.sleep(1 + attempt)
    return profile, "local_fallback"

def enrich_with_openai(profile: dict, resume_text: str, api_key: str) -> tuple[dict, str]:
    payload = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": AI_INSTRUCTIONS},
            {"role": "user", "content": resume_text[:30000]},
        ],
    }
    request = Request("https://api.openai.com/v1/chat/completions", data=json.dumps(payload).encode("utf-8"), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=20) as response:
            content = json.loads(response.read().decode("utf-8"))["choices"][0]["message"]["content"]
        return apply_ai_profile(profile, json.loads(content)), "openai"
    except (HTTPError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return profile, "local_fallback"

def enrich_profile_with_ai(profile: dict, resume_text: str) -> tuple[dict, str]:
    if gemini_key := os.getenv("GEMINI_API_KEY"):
        try:
            return enrich_with_gemini(profile, resume_text, gemini_key)
        except (HTTPError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    if openai_key := os.getenv("OPENAI_API_KEY"):
        try:
            return enrich_with_openai(profile, resume_text, openai_key)
        except (HTTPError, TimeoutError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            pass
    return profile, "local_fallback" if gemini_key or openai_key else "local"

@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "resufind-api"}

@app.post("/api/resumes/parse")
async def parse_resume(resume: UploadFile = File(...)) -> dict:
    content = await resume.read()
    if len(content) > 10 * 1024 * 1024: raise HTTPException(status_code=413, detail="Resume must be smaller than 10 MB.")
    if not resume.filename: raise HTTPException(status_code=400, detail="A resume filename is required.")
    text = extract_text(resume.filename, content)
    if not text.strip(): raise HTTPException(status_code=422, detail="No readable text was found in this resume.")
    profile, parser = enrich_profile_with_ai(parse_profile(text), text)
    return {"profile": profile, "parser": parser, "parsed_at": datetime.now(timezone.utc).isoformat()}

@app.post("/api/jobs/search")
def search_jobs(profile: SearchProfile) -> dict:
    query = profile.headline or "job"
    if profile.job_type.lower() == "internship":
        query = f"{query} internship"
    source_status = {}
    collected_jobs = []
    seen_ids = set()
    for provider in configured_providers(JOB_FIXTURES):
        try:
            provider_jobs = provider.search(query, profile.location)
            source_status[provider.name] = f"complete ({len(provider_jobs)} jobs)"
            for job in provider_jobs:
                if job["id"] not in seen_ids:
                    seen_ids.add(job["id"])
                    collected_jobs.append(job)
        except HTTPError as provider_error:
            source_status[provider.name] = f"failed: HTTP {provider_error.code}"
        except Exception as provider_error:
            source_status[provider.name] = f"failed: {type(provider_error).__name__}"
    ranked_jobs = sorted((score_job(profile, job) for job in collected_jobs if role_matches(profile, job) and location_matches(profile, job) and job_type_matches(profile, job)), key=lambda job: job["match_score"], reverse=True)
    ranked_jobs = [job for job in ranked_jobs if job["match_score"] >= 45]
    return {"jobs": ranked_jobs, "source_status": source_status}

@app.get("/api/saved-jobs")
def get_saved_jobs(user_id: str = "demo-user") -> dict:
    return {"jobs": list_saved_jobs(user_id)}

@app.post("/api/saved-jobs")
def create_saved_job(request: SavedJobRequest) -> dict:
    if not request.job.get("id"):
        raise HTTPException(status_code=400, detail="A job id is required.")
    return save_job(request.user_id, request.job)

@app.delete("/api/saved-jobs/{job_id}")
def delete_saved_job(job_id: str, user_id: str = "demo-user") -> dict:
    return {"deleted": remove_saved_job(user_id, job_id)}

@app.get("/api/alerts")
def get_alert_preferences(user_id: str = "demo-user") -> dict:
    return {"alert": get_alert(user_id)}

@app.post("/api/alerts")
def create_alert(request: AlertRequest) -> dict:
    if request.cadence not in {"daily", "weekly"}:
        raise HTTPException(status_code=400, detail="Cadence must be daily or weekly.")
    return {"alert": save_alert(request.user_id, request.email, request.cadence, request.profile.model_dump())}