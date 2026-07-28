# -*- coding: utf-8 -*-
"""
APPLIER AGENT — routes each Grade A job into one of three lanes and
prepares what's needed, WITHOUT secretly submitting anything.

Lanes:
  1. apply_pack  — portals where you apply on their site (LinkedIn, company
                   sites). The agent prepares a ready-to-use pack: the tailored
                   resume pointer, key talking points, and the direct link.
                   You click and submit — 2 minutes.
  2. outreach    — jobs better approached by emailing an HR/recruiter
                   (handled by the Outreach agent).
  3. auto_apply  — portals that technically allow it (Naukri/Internshala).
                   The lane is ASSIGNED here, but actual submission is a
                   separate, approval-gated step — never fired silently.

Why no silent auto-submit: submitting a real application is irreversible and
represents you. Your own rule is human-in-the-loop, and portals like LinkedIn
ban bot applications. So the agent prepares; you approve.
"""

from core import db


def _lane_for(job):
    portal = (job.get("portal") or "").lower()
    url    = job.get("apply_url") or ""
    if portal in ("naukri", "internshala"):
        return "auto_apply"          # assigned, still approval-gated to submit
    if not url:
        return "outreach"            # no link → better to email someone
    return "apply_pack"              # you apply on their site


def run(limit=30):
    """Assign lanes to ungrouped Grade A jobs. Returns lane counts."""
    res = (db.get_client().table("jobs")
           .select("id,title,company,portal,apply_url,lane")
           .eq("grade", "A").eq("lane", "none").limit(limit).execute())
    jobs = res.data or []
    if not jobs:
        db.log("applier", "No new Grade A jobs to route")
        return {}

    counts = {"apply_pack": 0, "outreach": 0, "auto_apply": 0}
    for j in jobs:
        lane = _lane_for(j)
        counts[lane] = counts.get(lane, 0) + 1
        db.get_client().table("jobs").update({"lane": lane}).eq("id", j["id"]).execute()

    db.log("applier", f"Routed {len(jobs)} Grade A jobs -> "
                      f"{counts['apply_pack']} apply-packs, "
                      f"{counts['outreach']} outreach, "
                      f"{counts['auto_apply']} auto-apply (all await your approval to submit)")
    return counts
