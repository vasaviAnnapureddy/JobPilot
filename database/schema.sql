-- ============================================================
-- JOBPILOT — DATABASE SCHEMA (Supabase / PostgreSQL)
-- Run this ONCE in Supabase: SQL Editor → New query → paste → Run
-- ============================================================

-- Enable vector extension for RAG (resume-job matching)
create extension if not exists vector;

-- ────────────────────────────────────────────────
-- 1. AGENT STATE — the master START/STOP switch
-- ────────────────────────────────────────────────
create table if not exists agent_state (
    key         text primary key,
    value       text not null,
    updated_at  timestamptz default now()
);

-- The switch itself + daily quotas (change from website Settings later)
insert into agent_state (key, value) values
    ('master_switch',      'stopped'),   -- 'running' | 'stopped'
    ('quota_auto_apply',   '10'),
    ('quota_apply_packs',  '10'),
    ('quota_outreach',     '10'),
    ('last_run_at',        ''),
    ('last_run_status',    '')
on conflict (key) do nothing;

-- ────────────────────────────────────────────────
-- 2. JOBS — every job the Scout finds
-- ────────────────────────────────────────────────
create table if not exists jobs (
    id            bigint generated always as identity primary key,
    found_at      timestamptz default now(),
    portal        text not null,              -- naukri / linkedin / indeed / internshala / cutshort ...
    title         text not null,
    company       text not null,
    location      text,
    salary        text,
    apply_url     text,
    description   text,
    -- Judge agent fills these:
    grade         text,                       -- A / B / C / D / F
    score         int,                        -- 0-100
    match_reason  text,                       -- evidence-based reason
    missing_skills text,                      -- comma separated
    resume_tip    text,
    scam_flags    text,                       -- Scam Shield findings, empty = clean
    -- Which lane it went to:
    lane          text default 'none',        -- auto_apply / apply_pack / outreach / none
    jd_embedding  vector(768),                -- for RAG matching
    unique (title, company)                   -- no duplicates
);

-- ────────────────────────────────────────────────
-- 3. APPLICATIONS — everything you actually applied to
-- ────────────────────────────────────────────────
create table if not exists applications (
    id             bigint generated always as identity primary key,
    job_id         bigint references jobs(id),
    applied_at     timestamptz default now(),
    method         text,                      -- auto / manual_pack / email_outreach
    resume_profile text,                      -- data_scientist / ml_engineer / data_analyst / genai
    resume_version text,                      -- filename of exact PDF sent
    status         text default 'applied',    -- applied / viewed / online_test / interview / offer / rejected / ghosted
    rejected_reason text,
    notes          text
);

-- ────────────────────────────────────────────────
-- 4. ROUNDS — your interview pipeline per application
-- ────────────────────────────────────────────────
create table if not exists rounds (
    id             bigint generated always as identity primary key,
    application_id bigint references applications(id),
    round_number   int,
    round_name     text,                      -- Online Test / Tech Round 1 / HR ...
    scheduled_at   timestamptz,
    status         text default 'pending',    -- pending / cleared / failed / skipped
    notes          text,                      -- "asked SQL joins, revise!"
    created_at     timestamptz default now()
);

-- ────────────────────────────────────────────────
-- 5. OUTREACH — every email sent to HRs / referrals
-- ────────────────────────────────────────────────
create table if not exists outreach (
    id             bigint generated always as identity primary key,
    job_id         bigint references jobs(id),
    sent_at        timestamptz,
    contact_name   text,
    contact_email  text,
    contact_role   text,                      -- HR / recruiter / employee_referral
    company        text,
    email_subject  text,
    email_body     text,
    research_notes text,                      -- what the agent learned about company/HR
    resume_version text,
    approved_by_me boolean default false,     -- HITL: nothing sends without this
    replied        boolean default false,
    reply_summary  text,
    followup_due   date,
    followup_sent  boolean default false
);

-- ────────────────────────────────────────────────
-- 6. RESUME PROFILES — your 4 versions + history
-- ────────────────────────────────────────────────
create table if not exists resume_profiles (
    id           bigint generated always as identity primary key,
    profile_name text unique,                 -- data_scientist / ml_engineer / data_analyst / genai
    content_md   text,                        -- the markdown content
    updated_at   timestamptz default now()
);

create table if not exists resume_edits (
    id           bigint generated always as identity primary key,
    profile_name text,
    job_id       bigint references jobs(id),
    suggestion   text,                        -- what AI proposed (before → after)
    ats_before   int,
    ats_after    int,
    approved     boolean default null,        -- null=pending, true/false = your decision (HITL)
    created_at   timestamptz default now()
);

-- ────────────────────────────────────────────────
-- 7. SKILL GAPS + WEEKLY INTELLIGENCE
-- ────────────────────────────────────────────────
create table if not exists skill_gaps (
    id          bigint generated always as identity primary key,
    week        date,
    skill       text,
    job_count   int,
    category    text,
    learned     boolean default false         -- you tick this on the website
);

create table if not exists weekly_reports (
    id          bigint generated always as identity primary key,
    week        date unique,
    report_md   text,                         -- full Intelligence Agent report
    created_at  timestamptz default now()
);

-- ────────────────────────────────────────────────
-- 8. AGENT LOGS — so failures are never silent
-- ────────────────────────────────────────────────
create table if not exists agent_logs (
    id          bigint generated always as identity primary key,
    ts          timestamptz default now(),
    agent       text,                         -- boss / scout / judge / ...
    level       text,                         -- INFO / WARN / ERROR
    message     text
);

-- Helpful indexes
create index if not exists idx_jobs_grade on jobs(grade);
create index if not exists idx_jobs_found on jobs(found_at);
create index if not exists idx_apps_status on applications(status);
create index if not exists idx_logs_ts on agent_logs(ts);
