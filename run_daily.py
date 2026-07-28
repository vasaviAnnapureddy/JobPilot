# -*- coding: utf-8 -*-
"""
JobPilot — DAILY RUN. This is what the scheduler calls each morning.

It: keeps the DB awake → runs the full agent team (if your switch is ON)
→ emails you the day's best jobs.

Manual:   python run_daily.py
Scheduled: setup_daily.bat registers this to run every morning.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

from core import db, keepalive
from agents import boss, notifier


def main():
    keepalive.ping()                      # stop Supabase pausing

    if not db.is_running():
        db.log("daily", "Master switch is OFF — skipping run. Turn on from the website.")
        return

    result = boss.run()                   # scout → judge → tailor → applier → outreach → tracker
    try:
        notifier.send()                   # email the best jobs
    except Exception as e:
        db.log("daily", f"Email step failed: {str(e)[:100]}", "ERROR")

    db.log("daily", f"Daily run done — Grade A: {result.get('grade_a', 0)}, "
                    f"suggestions: {result.get('suggestions', 0)}")


if __name__ == "__main__":
    main()
