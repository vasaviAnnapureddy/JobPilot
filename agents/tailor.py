# -*- coding: utf-8 -*-
"""
TAILOR AGENT — ATS scoring + resume edit SUGGESTIONS (human-in-the-loop).

What it DOES:
  - For each Grade A/B job, computes an ATS keyword-match score
    (how many of the job's important keywords appear in the resume).
  - Uses the LLM + RAG evidence to propose SPECIFIC, small edits
    ("add 'FastAPI' to your skills — the JD mentions it 3 times").
  - Stores each suggestion in the resume_edits table with approved = null.

What it DELIBERATELY DOES NOT DO:
  - It never rewrites or overwrites the resume. The candidate reviews
    each suggestion and ticks approve/reject on the website. This is
    the human-in-the-loop rule: the AI proposes, the human decides.
"""

import json
import re
from pathlib import Path

from core import db, llm, config, rag

STOP = set("a an the and or for to of in on with at by from as is are be this that "
           "you your we our will can role job work team using use etc".split())


def _load_resume():
    cv = config.RESUMES_DIR / "cv_master.md"
    return cv.read_text(encoding="utf-8") if cv.exists() else ""


def _keywords(text, top=30):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+.#]{2,}", (text or "").lower())
    freq = {}
    for w in words:
        if w not in STOP:
            freq[w] = freq.get(w, 0) + 1
    return sorted(freq, key=freq.get, reverse=True)[:top]


def ats_score(resume_text, job_desc):
    """Simple, explainable ATS score: % of job keywords present in resume."""
    jd_kw = _keywords(job_desc, top=25)
    if not jd_kw:
        return 0, []
    resume_low = resume_text.lower()
    missing = [k for k in jd_kw if k not in resume_low]
    matched = len(jd_kw) - len(missing)
    return round(100 * matched / len(jd_kw)), missing


SUGGEST_PROMPT = """A candidate is applying to this job. Suggest at most 4 SMALL, honest
resume edits that would improve keyword match — only things the candidate can
truthfully claim based on the evidence below. Never invent experience.

JOB TITLE: {title} at {company}
MISSING KEYWORDS (in job, not in resume): {missing}

CANDIDATE'S RELEVANT REAL EXPERIENCE (retrieved from their resume):
{evidence}

Reply as a JSON array of objects (max 4), each:
{{"change": "<what to add/reword, one line>",
  "where": "<which resume section>",
  "truthful": true/false  (false if it would require claiming something not supported by the evidence)}}
Only include truthful:true suggestions."""


def run(limit=15):
    """Score Grade A/B jobs and store edit suggestions for approval."""
    resume = _load_resume()
    if not resume:
        db.log("tailor", "No resume found", "ERROR")
        return 0
    rag.build_index()

    res = (db.get_client().table("jobs")
           .select("id,title,company,description")
           .in_("grade", ["A", "B"]).limit(limit).execute())
    jobs = res.data or []
    if not jobs:
        db.log("tailor", "No Grade A/B jobs to tailor for")
        return 0

    suggestions_made = 0
    for j in jobs:
        score, missing = ats_score(resume, j.get("description", ""))
        evidence = rag.retrieve(f"{j['title']} {j.get('description','')[:600]}", top_k=2)
        prompt = SUGGEST_PROMPT.format(
            title=j["title"], company=j["company"],
            missing=", ".join(missing[:12]) or "none",
            evidence=" || ".join(evidence) or "(general profile)",
        )
        try:
            edits = llm.ask_json(prompt, log_fn=lambda m: db.log("tailor", m, "WARN"))
        except Exception as e:
            db.log("tailor", f"Suggestion failed for job {j['id']}: {str(e)[:80]}", "WARN")
            continue

        for e in (edits or []):
            if isinstance(e, dict) and e.get("truthful") and e.get("change"):
                try:
                    db.get_client().table("resume_edits").insert({
                        "profile_name": "master",
                        "job_id": j["id"],
                        "suggestion": f"[{e.get('where','')}] {e['change']}",
                        "ats_before": score,
                        "approved": None,          # HITL: awaits your decision
                    }).execute()
                    suggestions_made += 1
                except Exception:
                    pass

    db.log("tailor", f"Done — reviewed {len(jobs)} jobs, "
                     f"stored {suggestions_made} edit suggestions (awaiting your approval)")
    return suggestions_made
