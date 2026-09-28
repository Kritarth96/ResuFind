import json
import os
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

KNOWN_SKILLS = ["Python", "TypeScript", "JavaScript", "React", "Next.js", "FastAPI", "SQL", "PostgreSQL", "Figma", "Product strategy", "User research", "Data analysis", "Machine learning", "AWS", "Docker", "Git", "Agile", "Communication"]
LOCATION_TRANSLATIONS = {"الهند": "India", "المملكة المتحدة": "United Kingdom", "الولايات المتحدة": "United States"}


class JobProvider(ABC):
    name: str

    @abstractmethod
    def search(self, query: str, location: str = "") -> list[dict]:
        raise NotImplementedError


class LocalFixtureProvider(JobProvider):
    name = "local_demo"

    def __init__(self, jobs: list[dict]):
        self.jobs = jobs

    def search(self, query: str, location: str = "") -> list[dict]:
        terms = {term.lower() for term in query.split() if len(term) > 2}
        if not terms:
            return self.jobs
        return [job for job in self.jobs if terms & {term.lower() for term in f"{job['title']} {job['description']} {' '.join(job['skills'])}".split()}] or self.jobs


class SerpApiProvider(JobProvider):
    name = "serpapi"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, location: str = "") -> list[dict]:
        is_remote = location.strip().lower() in {"remote", "remote only", "work from home"}
        params = {"engine": "google_jobs", "q": f"{query} remote jobs" if is_remote else query, "api_key": self.api_key}
        if location and not is_remote:
            params["location"] = location
        encoded_params = urlencode(params)
        request = Request(f"https://serpapi.com/search.json?{encoded_params}", headers={"User-Agent": "Resufind/0.1"})
        with urlopen(request, timeout=12) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return [self._normalize(item) for item in payload.get("jobs_results", [])]

    @staticmethod
    def _normalize(job: dict) -> dict:
        detected_extensions = job.get("detected_extensions", {})
        searchable_text = f"{job.get('title', '')} {job.get('description', '')}"
        skills = [skill for skill in KNOWN_SKILLS if skill.lower() in searchable_text.lower()]
        location = job.get("location", "Location not listed")
        for localized, english in LOCATION_TRANSLATIONS.items():
            location = location.replace(localized, english)
        return {
            "id": f"serpapi-{abs(hash(job.get('share_link', job.get('title', 'job'))))}",
            "title": job.get("title", "Untitled role"),
            "company": job.get("company_name", "Unknown company"),
            "location": location,
            "salary": job.get("salary", "Salary not listed"),
            "description": job.get("description", "No description provided."),
            "apply_link": job.get("apply_options", [{}])[0].get("link", job.get("share_link", "#")),
            "source": job.get("via", "Google Jobs"),
            "posted_date": detected_extensions.get("posted_at", datetime.now(timezone.utc).date().isoformat()),
            "job_type": detected_extensions.get("schedule", "Full-time"),
            "skills": skills,
        }


def configured_providers(jobs: list[dict]) -> list[JobProvider]:
    providers: list[JobProvider] = [LocalFixtureProvider(jobs)]
    if api_key := os.getenv("SERPAPI_KEY"):
        providers.append(SerpApiProvider(api_key))
    return providers