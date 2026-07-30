# -*- coding: utf-8 -*-
"""
Export the best jobs to docs/jobs.json for the FREE GitHub Pages site.

The static page (docs/index.html) reads this file — NO database, NO keys,
NO RLS. Simple and reliable. Re-run this (or let the daily job do it) to
refresh what the public site shows.

  python export_public.py
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent))
from core import db

DOCS = Path(__file__).resolve().parent / "docs"


def run():
    cols_with = "title,company,location,portal,score,grade,match_reason,apply_url,profile,found_at"
    cols_no   = "title,company,location,portal,score,grade,match_reason,apply_url,found_at"
    def _q(cols):
        return (db.get_client().table("jobs").select(cols)
                .in_("grade", ["A", "B"]).order("score", desc=True).limit(300)
                .execute().data or [])
    try:
        rows = _q(cols_with)
    except Exception:
        rows = _q(cols_no)          # migration_v2 not run yet — no profile column

    out = {
        "updated": datetime.now().strftime("%d %b %Y, %I:%M %p"),
        "count": len(rows),
        "jobs": rows,
    }
    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "jobs.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote docs/jobs.json — {len(rows)} jobs")
    return len(rows)


if __name__ == "__main__":
    run()
