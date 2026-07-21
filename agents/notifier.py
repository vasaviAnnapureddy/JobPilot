# -*- coding: utf-8 -*-
"""
NOTIFIER — sends a daily email of the best jobs from the database.

This is a bridge until the Django website (Stage 2) exists. It reads
graded jobs straight from Supabase and emails the top Grade A + B roles
with clickable apply links, scores, and the reason each one matched.
"""

import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core import db, config


def _top_jobs(grade, limit):
    res = (db.get_client().table("jobs")
           .select("title,company,location,portal,score,apply_url,match_reason,missing_skills,scam_flags")
           .eq("grade", grade).order("score", desc=True).limit(limit).execute())
    return res.data or []


def _job_card(job, rank):
    scam = ""
    if job.get("scam_flags"):
        scam = (f'<div style="background:#fff3cd;color:#856404;padding:6px 10px;'
                f'border-radius:4px;font-size:12px;margin-top:6px;">'
                f'⚠️ Check before applying: {job["scam_flags"][:120]}</div>')
    miss = ""
    if job.get("missing_skills"):
        miss = (f'<div style="font-size:12px;color:#888;margin-top:4px;">'
                f'To improve fit: {job["missing_skills"][:100]}</div>')
    url = job.get("apply_url") or "#"
    return f"""
    <div style="border:1px solid #e0e0e0;border-left:4px solid #28a745;border-radius:6px;
                padding:14px;margin:10px 0;background:#fafffb;">
      <div style="display:flex;justify-content:space-between;">
        <strong style="font-size:15px;color:#1a1a1a;">#{rank} {job['title']}</strong>
        <span style="background:#28a745;color:#fff;padding:2px 10px;border-radius:12px;
                     font-size:12px;font-weight:bold;height:fit-content;">{job['score']}/100</span>
      </div>
      <div style="color:#555;margin:3px 0;">{job['company']} · {job.get('location') or ''}
        <span style="color:#aaa;font-size:11px;">({job.get('portal','')})</span></div>
      <div style="font-size:13px;color:#444;margin-top:6px;">{job.get('match_reason','')[:160]}</div>
      {miss}{scam}
      <a href="{url}" style="display:inline-block;margin-top:10px;background:#2c5aa0;color:#fff;
         padding:7px 16px;border-radius:4px;text-decoration:none;font-size:13px;">Apply →</a>
    </div>"""


def send():
    sender = config.GMAIL_EMAIL
    pw     = config.GMAIL_APP_PASSWORD
    if not sender or not pw:
        db.log("notifier", "Gmail not configured in .env", "ERROR")
        return False

    grade_a = _top_jobs("A", 50)   # all Grade A jobs, no cap
    grade_b = _top_jobs("B", 15)

    if not grade_a and not grade_b:
        db.log("notifier", "No graded jobs to email yet", "WARN")
        return False

    a_cards = "".join(_job_card(j, i) for i, j in enumerate(grade_a, 1)) or \
              "<p style='color:#888;'>No Grade A jobs today.</p>"
    b_cards = "".join(_job_card(j, i) for i, j in enumerate(grade_b, 1))

    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    body = f"""
<html><body style="font-family:Arial,sans-serif;max-width:640px;margin:0 auto;color:#333;">
  <div style="background:linear-gradient(135deg,#1a237e,#4a86e8);padding:22px;border-radius:8px 8px 0 0;">
    <h2 style="color:#fff;margin:0;">🚀 JobPilot — Today's Best Jobs</h2>
    <p style="color:#c5d8ff;margin:4px 0 0;font-size:13px;">{now} · {len(grade_a)} top matches + {len(grade_b)} good matches</p>
  </div>
  <div style="padding:16px 4px;">
    <h3 style="color:#1a237e;">⭐ Apply Today — Grade A</h3>
    {a_cards}
    <h3 style="color:#1a237e;margin-top:24px;">👍 Also Worth It — Grade B</h3>
    {b_cards}
  </div>
  <p style="color:#aaa;font-size:11px;border-top:1px solid #eee;padding-top:12px;">
    Found by your JobPilot agent team. Full list lives in your database — the website (coming soon) will show all {len(grade_a)+len(grade_b)}+ jobs with tracking.
  </p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚀 JobPilot: {len(grade_a)} top jobs for you — {datetime.now():%d %b}"
    msg["From"] = sender
    msg["To"]   = sender
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as srv:
            srv.login(sender, pw)
            srv.sendmail(sender, sender, msg.as_string())
        db.log("notifier", f"Email sent — {len(grade_a)} Grade A, {len(grade_b)} Grade B")
        return True
    except Exception as e:
        db.log("notifier", f"Email failed: {str(e)[:100]}", "ERROR")
        return False


if __name__ == "__main__":
    send()
