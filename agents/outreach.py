# -*- coding: utf-8 -*-
"""
OUTREACH AGENT — drafts personalized HR/recruiter emails (human-in-the-loop).

What it DOES:
  - For jobs in the 'outreach' lane, drafts a short, personalized email
    that references the specific role and the candidate's most relevant
    real experience (pulled via RAG).
  - Stores each draft in the outreach table with approved_by_me = false.

What it DELIBERATELY DOES NOT DO:
  - It never sends. Sending an email represents the candidate and can't be
    undone. Every draft waits on the website for approval; only then is it
    sent. This is the human-in-the-loop rule.

Honest note on "company research": this draft is grounded in the job
description and the candidate's real experience. Deep live research of the
company/HR person (their recent posts, news) is a planned enhancement that
needs a web-search step — it is NOT claimed to happen here yet.
"""

from core import db, llm, rag, config


DRAFT_PROMPT = """Write a short, warm, professional outreach email (max 130 words) from a
fresher applying to this job. It must feel personal, not templated.

ROLE: {title} at {company}
CANDIDATE'S MOST RELEVANT REAL EXPERIENCE (use this, don't invent):
{evidence}

Rules:
- Open with genuine interest in THIS role/company.
- One or two sentences connecting the candidate's real experience to the role.
- Polite ask for consideration / a quick chat.
- Sign as "Vasavi Annapureddy".
Reply as JSON: {{"subject": "<subject line>", "body": "<email body>"}}"""


def run(limit=10):
    """Draft outreach emails for jobs in the outreach lane. Nothing is sent."""
    rag.build_index()
    res = (db.get_client().table("jobs")
           .select("id,title,company,description")
           .eq("grade", "A").eq("lane", "outreach").limit(limit).execute())
    jobs = res.data or []
    if not jobs:
        db.log("outreach", "No jobs in outreach lane")
        return 0

    drafted = 0
    for j in jobs:
        # Skip if a draft already exists for this job
        existing = (db.get_client().table("outreach")
                    .select("id").eq("job_id", j["id"]).execute())
        if existing.data:
            continue

        evidence = rag.retrieve(f"{j['title']} {j.get('description','')[:600]}", top_k=2)
        prompt = DRAFT_PROMPT.format(
            title=j["title"], company=j["company"],
            evidence=" || ".join(evidence) or "(general profile)",
        )
        try:
            draft = llm.ask_json(prompt, log_fn=lambda m: db.log("outreach", m, "WARN"))
        except Exception as e:
            db.log("outreach", f"Draft failed for job {j['id']}: {str(e)[:80]}", "WARN")
            continue

        if isinstance(draft, dict) and draft.get("body"):
            try:
                db.get_client().table("outreach").insert({
                    "job_id": j["id"],
                    "company": j["company"],
                    "contact_role": "HR / recruiter",
                    "email_subject": str(draft.get("subject", ""))[:200],
                    "email_body": str(draft["body"])[:2000],
                    "research_notes": "Drafted from job description + RAG resume evidence.",
                    "approved_by_me": False,     # HITL: never sent until you approve
                }).execute()
                drafted += 1
            except Exception:
                pass

    db.log("outreach", f"Done — drafted {drafted} outreach emails (awaiting your approval to send)")
    return drafted
