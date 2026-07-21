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


def run():
    """Search all portals, store new jobs, return count of new jobs found."""
    db.log("scout", "Starting job search across portals...")

    try:
        import job_search  # legacy module (proven: 290 jobs/run)
    except ImportError as e:
        db.log("scout", f"Cannot import legacy search: {e}", "ERROR")
        return 0

    all_rows = []

    # Portal 1+2: LinkedIn + Indeed via JobSpy
    try:
        df = job_search.fetch_jobspy_jobs()
        if df is not None and len(df):
            all_rows.extend(df.to_dict("records"))
            db.log("scout", f"LinkedIn/Indeed: {len(df)} jobs")
    except Exception as e:
        db.log("scout", f"JobSpy failed: {str(e)[:100]}", "WARN")

    # Portal 3: Naukri via browser interception
    try:
        df = job_search.fetch_naukri_jobs()
        if df is not None and len(df):
            all_rows.extend(df.to_dict("records"))
            db.log("scout", f"Naukri: {len(df)} jobs")
    except Exception as e:
        db.log("scout", f"Naukri failed: {str(e)[:100]}", "WARN")

    # Portal 4: Internshala
    try:
        df = job_search.fetch_internshala_jobs()
        if df is not None and len(df):
            all_rows.extend(df.to_dict("records"))
            db.log("scout", f"Internshala: {len(df)} jobs")
    except Exception as e:
        db.log("scout", f"Internshala failed: {str(e)[:100]}", "WARN")

    if not all_rows:
        db.log("scout", "No jobs found from any portal!", "ERROR")
        return 0

    clean = [_standardise(r) for r in all_rows]
    clean = [c for c in clean if c["title"] and c["company"]]
    new_count = db.insert_jobs(clean)

    db.log("scout", f"Done — {len(clean)} jobs found, {new_count} are NEW")
    return new_count
