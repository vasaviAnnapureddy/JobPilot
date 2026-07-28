# -*- coding: utf-8 -*-
"""
TRACKER AGENT — reads Gmail to keep application statuses up to date.

What it DOES (read-only on your inbox):
  - Scans recent emails for job-related messages.
  - Classifies each as: interview invite / rejection / acknowledgement.
  - If the sender's company matches an application you've logged, it
    updates that application's status automatically.
  - Flags interview invites so they are never missed.

What it does NOT do: it never sends, deletes, or replies to anything.
It only reads and updates your own tracking database.
"""

import imaplib
import email
import email.header
import re
from datetime import datetime, timedelta

from core import db, config

INTERVIEW_HINTS = ["interview", "shortlisted", "schedule a call", "technical round",
                   "assessment", "test invite", "next round", "availability", "hackerrank",
                   "coding round", "we'd like to speak", "move forward"]
REJECT_HINTS    = ["unfortunately", "not moving forward", "other candidates", "not selected",
                   "regret to inform", "not shortlisted", "position has been filled"]


def _decode(raw):
    if not raw:
        return ""
    out = []
    for part, enc in email.header.decode_header(raw):
        out.append(part.decode(enc or "utf-8", "replace") if isinstance(part, bytes) else str(part))
    return " ".join(out)


def _classify(subject, snippet):
    text = f"{subject} {snippet}".lower()
    if any(h in text for h in INTERVIEW_HINTS):
        return "interview"
    if any(h in text for h in REJECT_HINTS):
        return "rejected"
    return None


def run(days=7):
    """Scan recent inbox, classify job emails, update matching applications."""
    if not config.GMAIL_EMAIL or not config.GMAIL_APP_PASSWORD:
        db.log("tracker", "Gmail not configured", "WARN")
        return {}

    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(config.GMAIL_EMAIL, config.GMAIL_APP_PASSWORD)
        mail.select("inbox")
    except Exception as e:
        db.log("tracker", f"Gmail login failed: {str(e)[:80]}", "ERROR")
        return {}

    since = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
    _, nums = mail.search(None, f'(SINCE "{since}")')
    ids = nums[0].split() if nums and nums[0] else []

    # Load companies we've applied to, for matching
    apps = (db.get_client().table("applications")
            .select("id,job_id,status").execute()).data or []
    jobs = (db.get_client().table("jobs").select("id,company").execute()).data or []
    company_by_job = {j["id"]: (j.get("company") or "").lower() for j in jobs}

    found = {"interview": 0, "rejected": 0}
    for num in ids[-120:]:                    # scan most recent ~120
        try:
            _, data = mail.fetch(num, "(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM)])")
            hdr = data[0][1].decode("utf-8", "replace")
            subject = _decode(re.search(r"Subject: (.*)", hdr).group(1)) if "Subject:" in hdr else ""
            sender  = _decode(re.search(r"From: (.*)", hdr).group(1)) if "From:" in hdr else ""
        except Exception:
            continue

        kind = _classify(subject, sender)
        if not kind:
            continue

        # Try to match the sender's domain/name to an applied company
        for app in apps:
            comp = company_by_job.get(app["job_id"], "")
            if comp and len(comp) > 3 and comp.split()[0] in (subject + " " + sender).lower():
                if app["status"] not in ("interview", "offer"):
                    db.get_client().table("applications").update(
                        {"status": kind}).eq("id", app["id"]).execute()
                found[kind] += 1
                break

    try:
        mail.logout()
    except Exception:
        pass

    db.log("tracker", f"Scanned inbox — {found['interview']} interview signals, "
                      f"{found['rejected']} rejection signals matched to applications")
    return found
