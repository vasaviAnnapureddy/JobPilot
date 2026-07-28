# -*- coding: utf-8 -*-
"""
JUDGE AGENT — grades every new job against Vasavi's profile.

KEY DESIGN: BATCHED calls. The old system made 1 AI call per job
(290 jobs = 290 calls = quota death). The Judge grades 12 jobs in
ONE call → ~25 calls for 290 jobs → 91% fewer calls, no more 429s.

Stage 3 upgrade: RAG — retrieve her most relevant resume chunks per
job and grade with evidence. For now the profile brief is inline.
"""

import json
from pathlib import Path

from core import db, llm, config, rag


def _load_profile():
    cv = config.RESUMES_DIR / "cv_master.md"
    if cv.exists():
        return cv.read_text(encoding="utf-8")[:2500]
    return "B.Tech CSE (AI & ML) fresher, Python/ML/GenAI skills, Infosys & Wipro internships."


BATCH_PROMPT = """You are a strict career-match judge for this candidate:

=== CANDIDATE (fresher, 0 years full-time experience) ===
{profile}

=== JOBS TO GRADE (JSON array) ===
Each job includes "resume_evidence": the parts of the candidate's ACTUAL
resume most relevant to that job (retrieved by meaning). Use this evidence
to justify the match — cite specific projects/skills from it in your reason.
{jobs_json}

GRADING RULES:
- A (80-100): explicitly fresher/0-1yr friendly AND skills strongly match. Apply today.
- B (60-79): max 1 year required, minor gaps, competitive.
- C (40-59): says "1-2 years" OR notable skill gaps. Borderline.
- D (20-39): 2+ years required OR major gaps.
- F (0-19): senior role, 3+ years, or unrelated domain.

HARD RULES — automatic F if the description contains:
"2+ years", "3+ years", "minimum 2 years", "at least 2 years", "2-3 years",
"3-5 years", "senior", "lead", "principal", "manager", "director", "architect".

Also check each job for SCAM SIGNALS: registration fees, "pay for training",
salary too good to be true, WhatsApp-only contact, vague company identity.

Reply with ONLY a JSON array, one object per job, same order:
[{{"id": <job id>,
   "grade": "A|B|C|D|F",
   "score": <0-100>,
   "match_reason": "<one sentence, mention specific skills>",
   "missing_skills": "<comma separated or empty>",
   "resume_tip": "<one specific resume change for this job>",
   "scam_flags": "<warning text, or empty string if clean>"}}]"""


def _grade_batch(jobs, profile):
    """Grade one batch of jobs in a single AI call."""
    entries = []
    for j in jobs:
        job_text = f"{j['title']} at {j['company']}. {(j.get('description') or '')[:800]}"
        evidence = rag.retrieve(job_text, top_k=2)   # RAG: relevant resume parts
        entries.append({
            "id": j["id"],
            "title": j["title"],
            "company": j["company"],
            "location": j.get("location", ""),
            "description": (j.get("description") or "")[:1200],
            "resume_evidence": " || ".join(e[:300] for e in evidence) or "(none retrieved)",
        })
    jobs_json = json.dumps(entries, ensure_ascii=False)
    prompt = BATCH_PROMPT.format(profile=profile, jobs_json=jobs_json)
    result = llm.ask_json(prompt, log_fn=lambda m: db.log("judge", m, "WARN"))

    valid_ids = {j["id"] for j in jobs}
    rows = []
    for r in result:
        if isinstance(r, dict) and r.get("id") in valid_ids:
            rows.append({
                "id":             r["id"],
                "grade":          str(r.get("grade", "C"))[:1].upper(),
                "score":          int(r.get("score", 50)),
                "match_reason":   str(r.get("match_reason", ""))[:500],
                "missing_skills": str(r.get("missing_skills", ""))[:300],
                "resume_tip":     str(r.get("resume_tip", ""))[:300],
                "scam_flags":     str(r.get("scam_flags", ""))[:300],
            })
    return rows


def run():
    """Grade all ungraded jobs in the database. Returns (graded, grade_a) counts."""
    jobs = db.get_ungraded_jobs()
    if not jobs:
        db.log("judge", "No new jobs to grade")
        return 0, 0

    profile = _load_profile()
    n_chunks = rag.build_index()          # RAG: ensure resume is embedded (cached)
    db.log("judge", f"RAG index ready — {n_chunks} resume chunks")
    total_graded, grade_a = 0, 0
    batch_size = config.JUDGE_BATCH_SIZE

    db.log("judge", f"Grading {len(jobs)} jobs in batches of {batch_size} "
                    f"(~{(len(jobs) + batch_size - 1) // batch_size} AI calls)")

    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i + batch_size]
        try:
            rows = _grade_batch(batch, profile)
            db.save_grades([dict(r) for r in rows])
            total_graded += len(rows)
            grade_a += sum(1 for r in rows if r["grade"] == "A")
        except Exception as e:
            db.log("judge", f"Batch {i // batch_size + 1} failed: {str(e)[:100]}", "ERROR")
            continue  # one bad batch never kills the run

    db.log("judge", f"Done — {total_graded} graded, {grade_a} Grade A")
    return total_graded, grade_a
