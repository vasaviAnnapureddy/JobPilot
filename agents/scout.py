# -*- coding: utf-8 -*-
"""
SCOUT AGENT — finds jobs across portals and stores them in the database.

Stage 1: wraps the battle-tested legacy search (JobSpy + Naukri browser
interception + Internshala) that already found 290 jobs in one run.
Stage 3 will add adapters for Cutshort, Instahyre, Hirect, Wellfound.

Design rule (adapter pattern): each portal is one function that returns
a list of standard job dicts. Adding a portal in 2030 = adding one function.
"""

import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "legacy"))

from core import db


STANDARD_KEYS = ["portal", "title", "company", "location", "salary",
                 "apply_url", "description"]


def _standardise(raw_row):
    """Convert a legacy Excel-style row into a clean database row."""
    return {
        "portal":      str(raw_row.get("Portal", "unknown")).lower(),
        "title":       str(raw_row.get("Job Title", ""))[:300],
        "company":     str(raw_row.get("Company", ""))[:200],
        "location":    str(raw_row.get("Location", ""))[:200],
        "salary":      str(raw_row.get("Salary", ""))[:100],
        "apply_url":   str(raw_row.get("Apply Link", raw_row.get("URL", ""))),
        "description": str(raw_row.get("Description", raw_row.get("JD", "")))[:4000],
    }


def _active_profiles():
    """Profiles that have a resume file — these drive the searches."""
    from core import config
    active = [k for k in config.RESUME_PROFILES
              if (config.RESUMES_DIR / f"cv_{k}.md").exists()]
    return active or [config.DEFAULT_PROFILE]     # fall back to one default


def run():
    """Search per resume profile, tag each job with its profile, store new jobs."""
    from core import config
    db.log("scout", "Starting job search across portals...")

    try:
        import job_search  # legacy module (proven: 290 jobs/run)
    except ImportError as e:
        db.log("scout", f"Cannot import legacy search: {e}", "ERROR")
        return 0

    profiles = _active_profiles()
    db.log("scout", f"Active resume profiles: {', '.join(profiles)}")
    all_rows = []

    # LinkedIn + Indeed via JobSpy — run each profile's OWN searches, tag the jobs
    for profile in profiles:
        try:
            job_search.JOBSPY_SEARCHES = [(q, "India")
                                          for q in config.RESUME_PROFILES[profile]["searches"]]
        except Exception:
            pass
        try:
            df = job_search.fetch_jobspy_jobs()
            if df is not None and len(df):
                rows = df.to_dict("records")
                for r in rows:
                    r["_profile"] = profile        # tag with the resume it belongs to
                all_rows.extend(rows)
                db.log("scout", f"[{profile}] LinkedIn/Indeed: {len(df)} jobs")
        except Exception as e:
            db.log("scout", f"[{profile}] JobSpy failed: {str(e)[:80]}", "WARN")

    # Internshala — tag with the first active profile (single category set)
    try:
        df = job_search.fetch_internshala_jobs()
        if df is not None and len(df):
            rows = df.to_dict("records")
            for r in rows:
                r["_profile"] = profiles[0]
            all_rows.extend(rows)
            db.log("scout", f"Internshala: {len(df)} jobs")
    except Exception as e:
        db.log("scout", f"Internshala failed: {str(e)[:80]}", "WARN")

    if not all_rows:
        db.log("scout", "No jobs found from any portal!", "ERROR")
        return 0

    clean = []
    for r in all_rows:
        c = _standardise(r)
        c["profile"] = r.get("_profile", config.DEFAULT_PROFILE)
        if c["title"] and c["company"]:
            clean.append(c)
    new_count = db.insert_jobs(clean)

    db.log("scout", f"Done — {len(clean)} jobs found, {new_count} are NEW")
    return new_count
