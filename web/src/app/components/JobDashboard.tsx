"use client";

import { useEffect, useState } from "react";

export type Job = {
  id: string;
  title: string;
  company: string;
  location: string;
  salary: string;
  description: string;
  apply_link: string;
  source: string;
  posted_date: string;
  job_type: string;
  skills: string[];
  match_score: number;
  match_reasons: string[];
};

type Props = { jobs: Job[]; sourceStatus?: Record<string, string> };
const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function JobDashboard({ jobs, sourceStatus = {} }: Props) {
  const [sort, setSort] = useState("match");
  const [saved, setSaved] = useState<string[]>(() => {
    if (typeof window === "undefined") return [];
    return JSON.parse(window.localStorage.getItem("resufind-saved-jobs") ?? "[]") as string[];
  });
  const [expanded, setExpanded] = useState<string | null>(null);
  const [minimumScore, setMinimumScore] = useState("0");
  const [locationFilter, setLocationFilter] = useState("all");
  const [typeFilter, setTypeFilter] = useState("all");

  useEffect(() => { window.localStorage.setItem("resufind-saved-jobs", JSON.stringify(saved)); }, [saved]);

  async function toggleSaved(job: Job) {
    const alreadySaved = saved.includes(job.id);
    setSaved((current) => alreadySaved ? current.filter((item) => item !== job.id) : [...current, job.id]);
    try {
      if (alreadySaved) {
        await fetch(`${API_URL}/api/saved-jobs/${encodeURIComponent(job.id)}?user_id=demo-user`, { method: "DELETE" });
      } else {
        await fetch(`${API_URL}/api/saved-jobs`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ user_id: "demo-user", job }) });
      }
    } catch {
      // The local cache keeps the interaction usable when the API is offline.
    }
  }

  const filteredJobs = jobs.filter((job) => {
    const locationMatches = locationFilter === "all" || job.location.toLowerCase().includes(locationFilter);
    const typeMatches = typeFilter === "all" || job.job_type.toLowerCase().includes(typeFilter);
    return locationMatches && typeMatches && job.match_score >= Number(minimumScore);
  });
  const sortedJobs = [...filteredJobs].sort((first, second) => {
    if (sort === "date") return second.posted_date.localeCompare(first.posted_date);
    if (sort === "salary") return second.salary.localeCompare(first.salary, undefined, { numeric: true });
    return second.match_score - first.match_score;
  });

  return <section className="results" id="results" aria-label="Your job matches">
    <div className="results-header"><div><p className="eyebrow">04 / your shortlist</p><h2>Worth your<br /><em>attention.</em></h2></div><div className="results-count"><strong>{filteredJobs.length}</strong><span>of {jobs.length} curated matches<br />from your signal</span></div></div>
    <div className="provider-status">{Object.entries(sourceStatus).map(([source, status]) => <span key={source} className={status.startsWith("failed") ? "provider-failed" : ""}><i />{source.replace("_", " ")} · {status}</span>)}</div>
    <div className="results-toolbar"><label>Match <select value={minimumScore} onChange={(event) => setMinimumScore(event.target.value)}><option value="0">All scores</option><option value="70">70+ strong</option><option value="85">85+ excellent</option></select></label><label>Where <select value={locationFilter} onChange={(event) => setLocationFilter(event.target.value)}><option value="all">Everywhere</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="on-site">On-site</option></select></label><label>Type <select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}><option value="all">Any type</option><option value="full-time">Full-time</option><option value="contract">Contract</option><option value="part-time">Part-time</option><option value="intern">Internship</option></select></label><label>Sort <select value={sort} onChange={(event) => setSort(event.target.value)}><option value="match">Best match</option><option value="date">Newest first</option><option value="salary">Salary</option></select></label></div>
    {sortedJobs.length > 0 ? <div className="job-list">{sortedJobs.map((job) => <article className="job-card" key={job.id}><div className="score-column"><span className="score-ring">{job.match_score}</span><small>match</small></div><div className="job-main"><div className="job-meta"><span>{job.source}</span><span>{job.posted_date}</span></div><h3>{job.title}</h3><p className="company-line">{job.company} <span>·</span> {job.location}</p><p className="job-salary">{job.salary} <span>·</span> {job.job_type}</p><p className="job-description">{job.description}</p><div className="job-tags">{job.skills.map((skill) => <span key={skill}>{skill}</span>)}</div>{expanded === job.id && <div className="match-explainer"><strong>Why this match</strong><ul>{job.match_reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul></div>}</div><div className="job-actions"><button type="button" className={`save-button ${saved.includes(job.id) ? "saved" : ""}`} onClick={() => void toggleSaved(job)} aria-label={saved.includes(job.id) ? "Remove saved job" : "Save job"}>{saved.includes(job.id) ? "★" : "☆"}</button><button type="button" className="why-button" onClick={() => setExpanded(expanded === job.id ? null : job.id)}>{expanded === job.id ? "Hide why" : "Why this match?"}</button><a className="apply-button" href={job.apply_link} target="_blank" rel="noreferrer">Apply <span>↗</span></a></div></article>)}</div> : <div className="empty-results"><strong>No roles fit those filters.</strong><p>Try lowering the match score or widening the location and job type.</p><button type="button" onClick={() => { setMinimumScore("0"); setLocationFilter("all"); setTypeFilter("all"); }}>Reset filters</button></div>}
    {saved.length > 0 && <p className="saved-note">{saved.length} saved {saved.length === 1 ? "role" : "roles"}. Saved jobs will persist here once accounts are connected.</p>}
  </section>;
}
