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

# ── Location filter — only these cities (+ remote) ───
TARGET_CITIES = ["hyderabad", "pune", "chennai", "bangalore", "bengaluru",
                 "noida", "delhi", "gurgaon", "gurugram", "new delhi"]
REMOTE_WORDS = ["remote", "work from home", "wfh", "anywhere", "hybrid"]


def location_ok(loc):
    """True if the job is in a target city OR remote. Blank = allow (unknown)."""
    l = (loc or "").strip().lower()
    if not l:
        return True
    return any(c in l for c in TARGET_CITIES) or any(w in l for w in REMOTE_WORDS)

# ── Resume profiles ──────────────────────────────────
# Each profile = a resume version + the job searches it should trigger.
# Upload a resume and pick a profile → Scout searches THOSE jobs and the
# Judge grades against THAT resume. "Data Science resume → data science jobs."
RESUME_PROFILES = {
    "data_science": {
        "label": "Data Science",
        "searches": [
            "data scientist fresher", "junior data scientist",
            "data science associate", "machine learning engineer entry level",
            "data scientist python sql", "applied scientist fresher",
        ],
    },
    "ai_ml": {
        "label": "AI / ML Engineer",
        "searches": [
            "AI engineer fresher", "machine learning engineer entry level",
            "generative AI engineer junior", "LLM engineer python fresher",
            "deep learning engineer fresher", "AI ML fresher 2025",
        ],
    },
    "data_analyst": {
        "label": "Data Analyst",
        "searches": [
            "data analyst fresher", "data analyst python sql",
            "business analyst fresher", "analytics associate fresher",
            "power bi analyst fresher", "sql data analyst entry level",
        ],
    },
    "genai": {
        "label": "GenAI / LLM Engineer",
        "searches": [
            "generative AI engineer", "LLM engineer fresher",
            "prompt engineer fresher", "AI engineer RAG langchain",
            "NLP engineer junior", "genai developer fresher",
        ],
    },
}
DEFAULT_PROFILE = "ai_ml"

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
