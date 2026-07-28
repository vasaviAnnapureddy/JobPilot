-- ============================================================
-- JOBPILOT — MIGRATION v2 (run this ONE file in Supabase SQL Editor)
-- Includes: multi-resume columns + interview prep + referrals + practice log.
-- Safe to re-run (uses "if not exists").
-- ============================================================

-- ── Multi-resume + remote + portal division ──────────
alter table jobs add column if not exists profile   text default 'ai_ml';
alter table jobs add column if not exists work_type text;            -- onsite / remote / hybrid
alter table jobs add column if not exists is_remote boolean default false;
alter table jobs add column if not exists country   text default 'India';
alter table applications add column if not exists profile text default 'ai_ml';

-- ── Interview prep history ───────────────────────────
create table if not exists interview_prep (
    id          bigint generated always as identity primary key,
    created_at  timestamptz default now(),
    kind        text,          -- company_brief / mock_questions / answer_feedback / vocabulary / concept_coach
    company     text,
    role        text,
    question    text,
    response_md text
);

-- ── Referrals (drafted messages) ─────────────────────
create table if not exists referrals (
    id                bigint generated always as identity primary key,
    created_at        timestamptz default now(),
    company           text,
    role              text,
    connect_note      text,
    referral_message  text,
    search_url        text,
    status            text default 'drafted'   -- drafted / sent / connected / got_referral
);

-- ── Daily practice / study / learning log ────────────
-- One row per practice session. Powers your streaks & time totals.
create table if not exists practice_log (
    id          bigint generated always as identity primary key,
    logged_at   timestamptz default now(),
    day         date default current_date,
    kind        text,          -- leetcode / study / youtube / project / applications
    topic       text,          -- e.g. "Dynamic Programming", "Transformers"
    count       int default 0, -- e.g. problems solved
    minutes     int default 0, -- time spent
    link        text,          -- optional: leetcode/youtube url
    notes       text
);

create index if not exists idx_practice_day on practice_log(day);
create index if not exists idx_jobs_profile on jobs(profile);
