# -*- coding: utf-8 -*-
"""
JobPilot — DAILY RUN (bulletproof).

Design rule: this must NEVER crash and must ALWAYS try to email you.
Even if job scraping fails in the cloud (LinkedIn/Indeed often block
data-center IPs), you still get an email with the best jobs already in
your database.

Order:
  1. keep the database awake
  2. (best effort) run the agent team to find + grade new jobs
  3. ALWAYS email you the current best jobs

Manual:   python run_daily.py
Cloud:    GitHub Actions calls this every morning.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)


def safe(label, fn):
    """Run a step; log any failure but keep going."""
    try:
        return fn()
    except Exception as e:
        print(f"[daily] {label} failed (continuing): {str(e)[:160]}")
        return None


def main():
    # 0. Config check — clear message if secrets are missing
    from core import config
    if not config.DB_READY:
        print("[daily] ERROR: database not configured. In GitHub, add secrets "
              "SUPABASE_URL and SUPABASE_SECRET_KEY (Settings -> Secrets -> Actions).")
        return
    print(f"[daily] config OK | Gemini keys: {len(config.GEMINI_KEYS)} | Groq: {config.GROQ_READY}")

    from core import db, keepalive

    # 1. Keep DB awake
    safe("keepalive", keepalive.ping)

    # 2. Best-effort agent run (only if switch is ON)
    running = safe("switch check", db.is_running)
    if running:
        def run_team():
            from agents import boss
            r = boss.run()
            print(f"[daily] agents done — Grade A: {r.get('grade_a', 0)}, "
                  f"suggestions: {r.get('suggestions', 0)}")
        safe("agent team", run_team)
    else:
        print("[daily] switch is OFF — skipping search, but still emailing your best jobs.")

    # 3. ALWAYS email the current best jobs (this is the part that matters to you)
    def send_email():
        from agents import notifier
        ok = notifier.send()
        print(f"[daily] email sent: {ok}")
    safe("email", send_email)

    print("[daily] daily run complete.")


if __name__ == "__main__":
    main()
