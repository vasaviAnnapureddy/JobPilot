# -*- coding: utf-8 -*-
"""
REFERRAL FINDER — helps you get referrals (the #1 way freshers get hired).

Honest scope:
  - It does NOT scrape or store employees' names/emails (no LinkedIn API,
    and doing so risks your account + crosses privacy lines).
  - What it DOES: drafts a warm, personalized referral-request message
    grounded in YOUR real experience, and gives you the exact LinkedIn
    search link to find the right people to send it to. You send it.
"""

import urllib.parse
from core import db, llm, rag


REFERRAL_PROMPT = """Write TWO short LinkedIn messages a fresher can send to get a job referral.
Keep them warm, specific, and not desperate. Sign as "Vasavi".

COMPANY: {company}
ROLE she wants a referral for: {role}
HER RELEVANT REAL EXPERIENCE (use it, do not invent): {evidence}

Return JSON:
{{"connect_note": "<a 1-2 line note to send WITH a connection request, under 300 chars>",
  "referral_message": "<a short follow-up message asking for a referral once connected, 4-6 lines>",
  "tips": ["<3 short tips on who to approach and how>"]}}"""


def find_referral(company, role=""):
    rag.build_index()
    evidence = rag.retrieve(f"{role} at {company}", top_k=2)
    prompt = REFERRAL_PROMPT.format(
        company=company, role=role or "the role",
        evidence=" || ".join(evidence) or "(AI/ML fresher profile)",
    )
    try:
        data = llm.ask_json(prompt, log_fn=lambda m: db.log("referral", m, "WARN"))
    except Exception as e:
        return {"error": f"AI was busy — try again. ({str(e)[:60]})"}

    # The exact LinkedIn people-search to find employees to message
    kw = urllib.parse.quote(f"{company} {role}".strip())
    search_url = f"https://www.linkedin.com/search/results/people/?keywords={kw}&origin=SWITCH_SEARCH_VERTICAL"

    result = {
        "company": company,
        "role": role,
        "connect_note": data.get("connect_note", ""),
        "referral_message": data.get("referral_message", ""),
        "tips": data.get("tips", []),
        "search_url": search_url,
    }

    try:
        db.get_client().table("referrals").insert({
            "company": company, "role": role,
            "connect_note": result["connect_note"][:500],
            "referral_message": result["referral_message"][:2000],
            "search_url": search_url,
            "status": "drafted",
        }).execute()
    except Exception:
        pass   # table may not exist until migration is run — still return the draft
    return result
