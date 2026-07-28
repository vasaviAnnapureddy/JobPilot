# -*- coding: utf-8 -*-
"""
JobPilot — database layer (Supabase).
Every agent talks to the database ONLY through this file,
so if we ever change databases, only this file changes.
(That's the 10-year design.)
"""

import time
from datetime import datetime
from core import config

_client = None

# Errors that mean "the connection blipped" — safe to retry
_TRANSIENT = ("Server disconnected", "getaddrinfo failed", "RemoteProtocolError",
              "ConnectError", "Connection reset", "timed out", "ReadError",
              "Temporary failure")


def get_client(force_new=False):
    """Single shared Supabase client. force_new rebuilds it after a bad blip."""
    global _client
    if _client is None or force_new:
        if not config.DB_READY:
            raise RuntimeError(
                "Supabase not configured. Fill SUPABASE_URL and SUPABASE_KEY "
                "in JobPilot/.env (see SETUP.md step 1)."
            )
        from supabase import create_client
        _client = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
    return _client


def with_retry(fn, *, tries=4, base_delay=1.5):
    """
    Run a database operation, retrying on transient connection blips.
    Rebuilds the client between tries so a dropped connection recovers.
    This is what stops a momentary Supabase hiccup from crashing a run.
    """
    last = None
    for attempt in range(tries):
        try:
            return fn()
        except Exception as e:
            msg = str(e)
            last = e
            if any(t in msg for t in _TRANSIENT) and attempt < tries - 1:
                time.sleep(base_delay * (attempt + 1))
                try:
                    get_client(force_new=True)   # rebuild the connection
                except Exception:
                    pass
                continue
            raise
    raise last


# ────────────────────────────────────────────────
# AGENT STATE — the START/STOP switch
# ────────────────────────────────────────────────
def get_state(key, default=""):
    res = with_retry(lambda:
        get_client().table("agent_state").select("value").eq("key", key).execute())
    return res.data[0]["value"] if res.data else default


def set_state(key, value):
    with_retry(lambda: get_client().table("agent_state").upsert(
        {"key": key, "value": str(value), "updated_at": datetime.now().isoformat()}
    ).execute())


def is_running():
    """The master switch. Every agent checks this before working."""
    return get_state("master_switch", "stopped") == "running"


# ────────────────────────────────────────────────
# JOBS
# ────────────────────────────────────────────────
def insert_jobs(job_dicts):
    """Insert jobs, silently skipping duplicates (same title+company)."""
    inserted = 0
    for job in job_dicts:
        try:
            get_client().table("jobs").insert(job).execute()
            inserted += 1
        except Exception:
            pass  # duplicate — already found on a previous day
    return inserted


def get_ungraded_jobs(limit=200):
    res = with_retry(lambda: (get_client().table("jobs")
           .select("id,title,company,location,description")
           .is_("grade", "null")
           .limit(limit).execute()))
    return res.data or []


def save_grades(grade_rows):
    """grade_rows: list of {id, grade, score, match_reason, missing_skills, resume_tip}"""
    for row in grade_rows:
        job_id = row.pop("id")
        get_client().table("jobs").update(row).eq("id", job_id).execute()


# ────────────────────────────────────────────────
# LOGGING — failures are never silent
# ────────────────────────────────────────────────
def log(agent, message, level="INFO"):
    ts = datetime.now().strftime("%d-%b %H:%M")
    line = f"{ts} | {agent:<8} | {level:<5} | {message}"
    try:
        print(line)
    except UnicodeEncodeError:
        # Windows cp1252 console can't render some unicode — degrade gracefully
        print(line.encode("ascii", "replace").decode("ascii"))
    try:
        get_client().table("agent_logs").insert(
            {"agent": agent, "level": level, "message": message}
        ).execute()
    except Exception:
        pass  # DB down — at least we printed
