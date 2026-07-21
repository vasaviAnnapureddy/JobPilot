# JobPilot — Your Setup Steps (15 minutes, one time)

You do 3 things. Everything else is code that's already written.

---

## Step 1 — Supabase (the database) · 7 min

1. Go to **supabase.com** → sign in (you already have an account)
2. **New project** → name it `jobpilot` → choose region **Mumbai** → create
   (choose any strong database password, you won't need it daily)
3. Wait ~2 min for the project to be ready
4. Left sidebar → **SQL Editor** → **New query**
5. Open the file `database/schema.sql` from this folder → copy ALL of it → paste → **Run**
   → You should see "Success. No rows returned"
6. Left sidebar → ⚙️ **Settings** → **API** → copy two things:
   - **Project URL** (like `https://abcdxyz.supabase.co`)
   - **anon public** key (long text starting `eyJ...`)
7. Open `.env` in this folder → paste them into `SUPABASE_URL=` and `SUPABASE_KEY=`

## Step 2 — Groq (the free backup brain) · 3 min

1. Go to **console.groq.com** → sign up free (Google login works)
2. Left menu → **API Keys** → **Create API Key** → copy it
3. Paste into `.env` → `GROQ_API_KEY=`

## Step 3 — Test it · 2 min

Open a terminal in this folder and run:

```
python run_agent.py --status     (should show: master switch stopped)
python run_agent.py --start      (turns the team ON)
python run_agent.py              (one full workday: Scout finds → Judge grades)
```

If the last command prints "Run complete — found X, graded Y" → **JobPilot is alive.**

---

## Daily commands (until the website exists in Stage 2)

| Want | Command |
|---|---|
| Turn agent ON | `python run_agent.py --start` |
| Turn agent OFF | `python run_agent.py --stop` |
| Run a workday now | `python run_agent.py` |
| Check status | `python run_agent.py --status` |

## What exists after Stage 1

```
JobPilot/
├── run_agent.py          ← you run this
├── agents/
│   ├── boss.py           ← LangGraph supervisor + START/STOP
│   ├── scout.py          ← finds jobs (adapter pattern)
│   └── judge.py          ← grades in batches of 12 (no more quota crashes)
├── core/
│   ├── config.py         ← all settings in one place
│   ├── db.py             ← all database access in one place
│   └── llm.py            ← AI fallback chain (2 Gemini keys × 2 models + Groq)
├── database/schema.sql   ← the full database design (8 tables)
├── data/resumes/cv_master.md
└── legacy/job_search.py  ← proven search code (290 jobs/run)
```

## Coming next
- **Stage 2:** Django website — Command Center (START/STOP button), Today's Jobs, Application Tracker
- **Stage 3:** Resume Studio (ATS score + approve edits), 3 lanes (auto-apply / packs / outreach)
- **Stage 4:** Intelligence reports, Interview Prep, deploy to free cloud server
