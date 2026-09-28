"use client";

import { ChangeEvent, useState } from "react";
import JobDashboard, { Job } from "./components/JobDashboard";

type Profile = {
  name: string;
  headline: string;
  years_experience: string;
  location: string;
  skills: string[];
  roles: string[];
  education: string[];
  summary: string;
  expected_salary: string;
  industry: string;
};

const emptyProfile: Profile = { name: "", headline: "", years_experience: "", location: "", skills: [], roles: [], education: [], summary: "", expected_salary: "", industry: "" };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [profile, setProfile] = useState<Profile>(emptyProfile);
  const [skillInput, setSkillInput] = useState("");
  const [stage, setStage] = useState<"idle" | "uploading" | "ready" | "error">("idle");
  const [parserMode, setParserMode] = useState("local");
  const [error, setError] = useState("");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [sourceStatus, setSourceStatus] = useState<Record<string, string>>({});
  const [searching, setSearching] = useState(false);
  const [workMode, setWorkMode] = useState("Remote");
  const [jobType, setJobType] = useState("Full-time");

  async function parseResume(selectedFile: File) {
    setFile(selectedFile); setStage("uploading"); setError("");
    const body = new FormData(); body.append("resume", selectedFile);
    try {
      const response = await fetch(`${API_URL}/api/resumes/parse`, { method: "POST", body });
      if (!response.ok) throw new Error("The resume could not be parsed.");
      const parsed = await response.json();
      setProfile({ ...emptyProfile, ...parsed.profile, skills: parsed.profile.skills ?? [] }); setParserMode(parsed.parser ?? "local"); setStage("ready");
    } catch (parseError) { setStage("error"); setError(parseError instanceof Error ? parseError.message : "Something went wrong."); }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) { const selectedFile = event.target.files?.[0]; if (selectedFile) void parseResume(selectedFile); }
  function addSkill() { const skill = skillInput.trim(); if (skill && !profile.skills.includes(skill)) setProfile((current) => ({ ...current, skills: [...current.skills, skill] })); setSkillInput(""); }
  function removeSkill(skill: string) { setProfile((current) => ({ ...current, skills: current.skills.filter((item) => item !== skill) })); }
  function updateField(field: keyof Profile, value: string) { setProfile((current) => ({ ...current, [field]: value })); }
  async function buildShortlist() {
    setSearching(true); setError("");
    try {
      const response = await fetch(`${API_URL}/api/jobs/search`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...profile, work_mode: workMode, job_type: jobType }) });
      if (!response.ok) throw new Error("We could not build your shortlist.");
      const result = await response.json(); setJobs(result.jobs); setSourceStatus(result.source_status ?? {}); document.getElementById("results")?.scrollIntoView({ behavior: "smooth" });
    } catch (searchError) { setError(searchError instanceof Error ? searchError.message : "Something went wrong."); }
    finally { setSearching(false); }
  }

  return (
    <main className="site-shell">
      <nav className="topbar"><a className="wordmark" href="#top" aria-label="Resufind home"><span className="wordmark-mark">r</span>resufind</a><div className="nav-status"><span className="status-dot" /> AI job search, made personal</div></nav>
      <section className="hero" id="top"><div className="hero-copy"><p className="eyebrow">01 / your search signal</p><h1>Find work that<br /><em>fits the whole you.</em></h1><p className="hero-intro">Drop in your resume. Tell us where you want to go. Resufind turns the noisy job market into a shortlist worth your time.</p><div className="hero-note"><span>✳</span><span>Built for the next chapter,<br />not just the next application.</span></div></div><div className="hero-orbit" aria-hidden="true"><div className="orbit-ring ring-one" /><div className="orbit-ring ring-two" /><div className="orbit-core"><span>r</span></div><span className="orbit-label label-top">your signal</span><span className="orbit-label label-right">better fit</span><span className="orbit-label label-bottom">less noise</span></div></section>
      <section className="workspace" aria-label="Create your job search profile"><div className="section-heading"><p className="eyebrow">02 / make it yours</p><h2>Start with the story<br />behind your <em>resume.</em></h2></div><div className="workspace-grid"><div className="upload-column"><div className={`upload-zone ${stage === "ready" ? "is-ready" : ""}`}><input id="resume-upload" type="file" accept=".pdf,.docx" onChange={handleFileChange} /><label htmlFor="resume-upload"><span className="upload-icon">↑</span><strong>{file ? file.name : "Upload your resume"}</strong><span>{stage === "uploading" ? "Reading your experience..." : "PDF or DOCX · max 10 MB"}</span></label></div>{stage === "uploading" && <div className="progress-line"><span /></div>}{stage === "error" && <p className="error-message">{error} Make sure the API is running, then try again.</p>}{stage === "ready" && <p className="success-message">✓ Profile signal found · {parserMode === "gemini" || parserMode === "openai" ? `${parserMode === "gemini" ? "Gemini" : "OpenAI"} enriched` : parserMode === "local_fallback" ? "AI unavailable, local profile kept" : "local extraction"}.</p>}<div className="privacy-note"><span>◇</span><p>Your resume stays yours. It is used to build your search signal and never shared with employers without your say-so.</p></div></div><form className="profile-form" onSubmit={(event) => event.preventDefault()}><div className="form-row two-up"><label><span>Your name</span><input value={profile.name} onChange={(event) => updateField("name", event.target.value)} placeholder="e.g. Maya Chen" /></label><label><span>Years of experience</span><input value={profile.years_experience} onChange={(event) => updateField("years_experience", event.target.value)} placeholder="e.g. 5" /></label></div><label><span>What role are you looking for?</span><input value={profile.headline} onChange={(event) => updateField("headline", event.target.value)} placeholder="e.g. Product Designer, Data Analyst..." /></label><label><span>Where should we look?</span><input value={profile.location} onChange={(event) => updateField("location", event.target.value)} placeholder="e.g. New York, London, or Remote" /></label><div className="form-row two-up"><label><span>Expected salary</span><input value={profile.expected_salary} onChange={(event) => updateField("expected_salary", event.target.value)} placeholder="e.g. $120k+" /></label><label><span>Industry preference</span><input value={profile.industry} onChange={(event) => updateField("industry", event.target.value)} placeholder="e.g. Fintech, health, climate" /></label></div><div className="form-label"><span>Your skills</span><div className="skill-list">{profile.skills.map((skill) => <button type="button" className="skill-chip" key={skill} onClick={() => removeSkill(skill)}>{skill} <b>×</b></button>)}</div><div className="skill-entry"><input value={skillInput} onChange={(event) => setSkillInput(event.target.value)} placeholder="Add a skill" /><button type="button" onClick={addSkill} aria-label="Add skill">+</button></div></div><button className="primary-button" type="button" onClick={() => document.getElementById("preferences")?.scrollIntoView({ behavior: "smooth" })}>Continue to preferences <span>↗</span></button></form></div></section>
      <section className="preferences" id="preferences"><div><p className="eyebrow">03 / your north star</p><h2>Good work starts<br />with <em>good context.</em></h2></div><div className="preference-list"><div><span className="pref-number">01</span><p>Preferred work mode</p><div className="segmented">{["Remote", "Hybrid", "On-site"].map((mode) => <button type="button" key={mode} className={workMode === mode ? "selected" : ""} onClick={() => setWorkMode(mode)}>{mode}</button>)}</div></div><div><span className="pref-number">02</span><p>Job type</p><div className="segmented">{["Full-time", "Contract", "Part-time", "Internship"].map((type) => <button type="button" key={type} className={jobType === type ? "selected" : ""} onClick={() => setJobType(type)}>{type}</button>)}</div></div><button className="search-button" type="button" onClick={buildShortlist} disabled={searching}>{searching ? "Finding your fit..." : "Build my shortlist"} <span>→</span></button>{error && <p className="error-message">{error}</p>}</div></section>
      {jobs.length > 0 && <JobDashboard jobs={jobs} sourceStatus={sourceStatus} />}
      <footer><a className="wordmark" href="#top"><span className="wordmark-mark">r</span>resufind</a><span>More signal. Less scrolling.</span><span>© 2026</span></footer>
    </main>
  );
}
