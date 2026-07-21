# -*- coding: utf-8 -*-
"""
KEEP-ALIVE — touches the database once so Supabase never marks the
project 'inactive' and pauses it.

Supabase free tier pauses a project after ~7 days with zero requests.
Running this even once every few days resets that timer. Cheap and
instant — one tiny read.

Schedule it (or let the daily agent run cover it — a normal workday
already touches the DB, so this is only needed on days the agent
doesn't run).
"""

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import db


def ping():
    try:
        db.get_state("master_switch")           # one tiny read
        db.set_state("last_keepalive", datetime.now().isoformat())
        print(f"{datetime.now():%d-%b %H:%M} | keep-alive OK — Supabase stays awake")
        return True
    except Exception as e:
        print(f"{datetime.now():%d-%b %H:%M} | keep-alive FAILED: {str(e)[:100]}")
        return False


if __name__ == "__main__":
    ping()
