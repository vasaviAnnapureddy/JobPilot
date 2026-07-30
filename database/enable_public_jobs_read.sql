-- ============================================================
-- Let the FREE GitHub Pages site read your JOBS (read-only, public).
-- Your personal data (applications, outreach, resumes) stays PRIVATE.
-- Run this ONCE in Supabase -> SQL Editor.
-- ============================================================

-- Make sure row-level security is on for jobs
alter table jobs enable row level security;

-- Allow anyone to READ the jobs table (job listings + AI grades are not sensitive)
drop policy if exists "public read jobs" on jobs;
create policy "public read jobs"
  on jobs for select
  to anon
  using (true);

-- IMPORTANT: do NOT add read policies for these — keep them private:
--   applications, outreach, resume_edits, resume_profiles, agent_state, interview_prep
-- They already block anonymous access by default, so your personal data stays safe.
