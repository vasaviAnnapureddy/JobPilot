# -*- coding: utf-8 -*-
"""JobPilot — central configuration. Everything reads from here."""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ── Database ──────────────────────────────────────────
# Backend agents use the SECRET key (full access, trusted code on
# your machine/server). The publishable key is only for future
# public-facing pages.
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = (os.getenv("SUPABASE_SECRET_KEY", "").strip()
                or os.getenv("SUPABASE_KEY", "").strip())
DB_READY = bool(
    SUPABASE_URL and SUPABASE_KEY
    and "PASTE_YOUR" not in SUPABASE_URL
    and "PASTE_YOUR" not in SUPABASE_KEY
)

# ── AI models (fallback chain — order matters) ────────
GEMINI_KEYS = [
    k for k in [
        os.getenv("GEMINI_API_KEY", "").strip(),
        os.getenv("GEMINI_API_KEY_2", "").strip(),
    ] if k and "PASTE_YOUR" not in k
]
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_READY   = bool(GROQ_API_KEY and "PASTE_YOUR" not in GROQ_API_KEY)

GEMINI_MODELS = ["gemini-flash-lite-latest", "gemini-flash-latest"]
GROQ_MODEL    = "llama-3.3-70b-versatile"

# ── Batching (the fix for quota crashes) ─────────────
JUDGE_BATCH_SIZE = 12          # jobs graded per single AI call

# ── Portals / credentials ─────────────────────────────
NAUKRI_EMAIL      = os.getenv("NAUKRI_EMAIL", "")
NAUKRI_PASSWORD   = os.getenv("NAUKRI_PASSWORD", "")
LINKEDIN_EMAIL    = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")
GMAIL_EMAIL       = os.getenv("GMAIL_EMAIL", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# ── Paths ─────────────────────────────────────────────
RESUMES_DIR = BASE_DIR / "data" / "resumes"
LOGS_DIR    = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)
