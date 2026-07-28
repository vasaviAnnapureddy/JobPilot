-- ============================================================
-- JOBPILOT — MIGRATION: multi-resume + remote + portal division
-- Run this ONCE in Supabase → SQL Editor (after the first schema.sql)
-- Safe to re-run: uses "if not exists".
-- ============================================================

-- Tag every job with which resume profile it belongs to
alter table jobs add column if not exists profile text default 'ai_ml';

-- Remote / work-type info (for India remote + future foreign remote)
alter table jobs add column if not exists work_type text;         -- onsite / remote / hybrid
alter table jobs add column if not exists is_remote boolean default false;
alter table jobs add column if not exists country   text default 'India';

-- Tag applications with the resume profile too
alter table applications add column if not exists profile text default 'ai_ml';

-- Store the interview-prep company briefs you request
create table if not exists interview_prep (
    id           bigint generated always as identity primary key,
    created_at   timestamptz default now(),
    kind         text,              -- 'company_brief' / 'mock_questions' / 'answer_feedback' / 'vocabulary'
    company      text,
    role         text,
    question     text,              -- what you asked
    response_md  text               -- the AI's answer
);

create index if not exists idx_jobs_profile on jobs(profile);
create index if not exists idx_jobs_remote  on jobs(is_remote);
