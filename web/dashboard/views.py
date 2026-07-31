# -*- coding: utf-8 -*-
"""JobPilot dashboard views — read/write the Supabase data via core.db."""

import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from core import db


def _client():
    return db.get_client()


def _count(table, **filters):
    q = _client().table(table).select("id", count="exact")
    for k, v in filters.items():
        q = q.eq(k, v)
    try:
        return q.execute().count or 0
    except Exception:
        return 0


# ── Command Center (home) ────────────────────────────
def command_center(request):
    running = db.is_running()
    ctx = {
        "running":       running,
        "last_run_at":   db.get_state("last_run_at", "never"),
        "last_status":   db.get_state("last_run_status", "-"),
        "total_jobs":    _count("jobs"),
        "grade_a":       _count("jobs", grade="A"),
        "pending_edits": _count("resume_edits", approved=None) if False else _pending_edits(),
        "pending_drafts": _pending_drafts(),
        "applied":       _count("applications", status="applied"),
        "quota_auto":    db.get_state("quota_auto_apply", "10"),
        "quota_pack":    db.get_state("quota_apply_packs", "10"),
        "quota_out":     db.get_state("quota_outreach", "10"),
    }
    return render(request, "dashboard/command_center.html", ctx)


def _pending_edits():
    try:
        return _client().table("resume_edits").select("id", count="exact").is_("approved", "null").execute().count or 0
    except Exception:
        return 0


def _pending_drafts():
    try:
        return _client().table("outreach").select("id", count="exact").eq("approved_by_me", False).execute().count or 0
    except Exception:
        return 0


@require_POST
def toggle_switch(request):
    new = "stopped" if db.is_running() else "running"
    db.set_state("master_switch", new)
    return redirect("command_center")


# ── Today's Jobs ─────────────────────────────────────
def jobs(request):
    from core import config
    grade   = request.GET.get("grade", "A")
    lane    = request.GET.get("lane", "")
    day     = request.GET.get("day", "")
    profile = request.GET.get("profile", "")

    # select with profile if the column exists; fall back if not
    cols_with = "id,title,company,location,portal,score,grade,lane,apply_url,match_reason,missing_skills,scam_flags,found_at,profile"
    cols_no   = "id,title,company,location,portal,score,grade,lane,apply_url,match_reason,missing_skills,scam_flags,found_at"
    def _query(cols):
        q = _client().table("jobs").select(cols).order("score", desc=True).limit(300)
        if grade: q = q.eq("grade", grade)
        if lane:  q = q.eq("lane", lane)
        return q.execute().data or []
    try:
        rows = _query(cols_with)
        has_profiles = True
    except Exception:
        rows = _query(cols_no)
        has_profiles = False

    # profile tabs (labels + counts) — uses YOUR custom resume names
    from core import profiles as P
    profile_tabs = []
    if has_profiles:
        counts = {}
        for r in rows:
            counts[r.get("profile") or "ai_ml"] = counts.get(r.get("profile") or "ai_ml", 0) + 1
        for key, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            profile_tabs.append({"key": key, "label": P.label_for(key), "count": cnt})
        if profile:
            rows = [r for r in rows if (r.get("profile") or "ai_ml") == profile]

    # add a short date (DD/MM) + remote flag to each row
    for r in rows:
        fa = str(r.get("found_at") or "")[:10]        # YYYY-MM-DD
        r["day"] = fa
        r["day_short"] = (fa[8:10] + "/" + fa[5:7]) if len(fa) == 10 else "—"
        loc = (r.get("location") or "").lower()
        r["remote"] = ("remote" in loc or "work from home" in loc or "wfh" in loc)

    # date summary: how many jobs found each day (across all grades)
    all_dates = (_client().table("jobs").select("found_at").limit(1000).execute().data or [])
    from collections import Counter
    by_day = Counter(str(d.get("found_at") or "")[:10] for d in all_dates if d.get("found_at"))
    date_summary = [{"day": d, "day_short": d[8:10] + "/" + d[5:7], "count": c}
                    for d, c in sorted(by_day.items(), reverse=True)]

    if day:
        rows = [r for r in rows if r["day"] == day]

    return render(request, "dashboard/jobs.html",
                  {"jobs": rows, "grade": grade, "lane": lane, "day": day,
                   "count": len(rows), "date_summary": date_summary,
                   "profile_tabs": profile_tabs, "profile": profile})


# ── Application Tracker ──────────────────────────────
ROUND_STAGES = ["Applied", "Online Test", "Tech Round 1", "Tech Round 2", "HR Round", "Offer"]


def tracker(request):
    apps = (_client().table("applications")
            .select("id,job_id,status,method,resume_profile,applied_at,notes")
            .order("applied_at", desc=True).limit(100).execute().data or [])
    # attach company/title
    job_ids = [a["job_id"] for a in apps if a.get("job_id")]
    jobmap = {}
    if job_ids:
        jrows = _client().table("jobs").select("id,title,company").in_("id", job_ids).execute().data or []
        jobmap = {j["id"]: j for j in jrows}
    for a in apps:
        j = jobmap.get(a.get("job_id"), {})
        a["title"] = j.get("title", "—")
        a["company"] = j.get("company", "—")
    return render(request, "dashboard/tracker.html",
                  {"apps": apps, "stages": ROUND_STAGES})


@require_POST
def update_application(request):
    app_id = request.POST.get("app_id")
    status = request.POST.get("status")
    notes  = request.POST.get("notes")
    upd = {}
    if status:
        upd["status"] = status
    if notes is not None:
        upd["notes"] = notes
    if app_id and upd:
        _client().table("applications").update(upd).eq("id", app_id).execute()
    return redirect("tracker")


# ── Outreach Book ────────────────────────────────────
def outreach_book(request):
    rows = (_client().table("outreach")
            .select("id,company,contact_role,email_subject,email_body,approved_by_me,replied,sent_at")
            .order("id", desc=True).limit(100).execute().data or [])
    return render(request, "dashboard/outreach.html", {"rows": rows})


# ── Resume Studio (HITL approvals) ───────────────────
def resume_studio(request):
    rows = (_client().table("resume_edits")
            .select("id,suggestion,ats_before,approved,job_id")
            .order("id", desc=True).limit(100).execute().data or [])
    pending = [r for r in rows if r.get("approved") is None]
    decided = [r for r in rows if r.get("approved") is not None]
    return render(request, "dashboard/resume.html",
                  {"pending": pending, "decided": decided})


@require_POST
def decide_edit(request):
    edit_id = request.POST.get("edit_id")
    decision = request.POST.get("decision") == "approve"
    if edit_id:
        _client().table("resume_edits").update({"approved": decision}).eq("id", edit_id).execute()
    return redirect("resume")


# ── My Resumes (upload files / paste — one per job type) ─
def _extract_text(uploaded):
    """Read text from an uploaded resume file (.txt/.md/.pdf/.docx)."""
    import io
    name = uploaded.name.lower()
    data = uploaded.read()
    try:
        if name.endswith((".txt", ".md")):
            return data.decode("utf-8", "replace")
        if name.endswith(".pdf"):
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(data))
            return "\n".join((pg.extract_text() or "") for pg in reader.pages)
        if name.endswith(".docx"):
            import docx
            d = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in d.paragraphs)
    except Exception:
        return ""
    return ""


def my_resume(request):
    from core import rag, profiles as P
    saved_profile, error = None, None

    if request.method == "POST":
        action = request.POST.get("action", "add")
        if action == "delete":
            slug = request.POST.get("slug", "")
            if slug:
                P.delete_profile(slug)
            return redirect("my_resume")

        # add / update a named resume
        name = request.POST.get("name", "").strip()
        text = request.POST.get("resume", "").strip()
        up = request.FILES.get("resume_file")
        if up and not text:
            text = _extract_text(up).strip()
            if not text:
                error = f"Could not read '{up.name}'. Try a .txt/.pdf/.docx, or paste the text."
        if name and text and not error:
            slug = P.add_profile(name, text)
            try:
                rag.build_index(slug, force=True)   # embed this resume on its own
            except Exception:
                pass
            saved_profile = name
        elif not error:
            error = "Please enter a name AND paste text or upload a file."

    resumes = P.list_profiles()
    for r in resumes:
        r["searches_short"] = ", ".join(r["searches"][:3]) + " …"
    return render(request, "dashboard/my_resume.html",
                  {"resumes": resumes, "saved_profile": saved_profile, "error": error})


# ── Mark a job as applied (feeds the Tracker) ────────
@require_POST
def mark_applied(request):
    job_id = request.POST.get("job_id")
    if job_id:
        try:
            # avoid duplicate application rows for the same job
            existing = _client().table("applications").select("id").eq("job_id", job_id).execute()
            if not existing.data:
                _client().table("applications").insert({
                    "job_id": int(job_id), "status": "applied", "method": "manual_pack",
                }).execute()
        except Exception:
            pass
    return redirect(request.META.get("HTTP_REFERER", "/jobs/"))


# ── Interview Prep ───────────────────────────────────
def interview_prep_page(request):
    from agents import interview_prep as ip
    result, heading = None, None
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            if action == "brief":
                company = request.POST.get("company", "").strip()
                role = request.POST.get("role", "").strip()
                heading = f"Company brief — {company}"
                result = ip.company_brief(company, role) if company else "Enter a company name."
            elif action == "mock":
                role = request.POST.get("role", "").strip()
                heading = f"Mock questions — {role}"
                result = ip.mock_questions(role) if role else "Enter a role."
            elif action == "feedback":
                q = request.POST.get("q", "").strip()
                a = request.POST.get("a", "").strip()
                heading = "Feedback on your answer"
                result = ip.answer_feedback(q, a) if a else "Paste your practice answer."
            elif action == "vocab":
                t = request.POST.get("t", "").strip()
                heading = "Polished vocabulary"
                result = ip.vocabulary(t) if t else "Paste some text."
            elif action == "concept":
                topic = request.POST.get("topic", "").strip()
                heading = f"Concept coach — {topic}"
                result = ip.concept_coach(topic) if topic else "Enter a topic."
        except Exception as e:
            result = f"The AI was busy — try again in a moment. ({str(e)[:80]})"
    # recent history
    try:
        history = (_client().table("interview_prep")
                   .select("kind,company,role,question,created_at")
                   .order("id", desc=True).limit(8).execute().data or [])
    except Exception:
        history = []
    return render(request, "dashboard/interview.html",
                  {"result": result, "heading": heading, "history": history})


# ── Grow & Practice (referrals + LeetCode coach) ─────
def grow_page(request):
    from core import practice
    referral, coach = None, None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "referral":
            from agents import referral_finder as rf
            company = request.POST.get("company", "").strip()
            role = request.POST.get("role", "").strip()
            if company:
                referral = rf.find_referral(company, role)
        elif action == "log":
            practice.add(
                name=request.POST.get("name", "")[:150],
                difficulty=request.POST.get("difficulty", "Easy"),
                topic=request.POST.get("topic", "")[:100],
                minutes=request.POST.get("minutes") or 0,
                kind=request.POST.get("kind", "leetcode"),
            )
            return redirect("grow")
        elif action == "coach_me":
            from agents import coding_coach as cc
            coach = {"title": "Your next steps", "text": cc.next_for_me()}
        elif action == "coach_company":
            from agents import coding_coach as cc
            company = request.POST.get("company", "").strip()
            if company:
                coach = {"title": f"Coding plan for {company}", "text": cc.for_company(company)}

    return render(request, "dashboard/grow.html", {
        "referral": referral, "coach": coach,
        "entries": practice.entries(15), "s": practice.summary(),
    })


# ── Video Mock Interview ─────────────────────────────
DEFAULT_MOCK_QS = [
    "Tell me about yourself and why you want this role.",
    "Walk me through one project you're proud of, end to end.",
    "Explain a machine learning concept you know well, simply.",
    "Tell me about a time you faced a hard bug or problem. How did you solve it?",
    "What are your strengths and one weakness you're working on?",
    "Where do you see yourself in the AI/data field in 3 years?",
]


def mock_interview_page(request):
    role = request.GET.get("role", "").strip()
    questions = DEFAULT_MOCK_QS
    if role:
        # Try to generate role-specific questions; fall back to defaults
        try:
            from agents import interview_prep as ip
            raw = ip.mock_questions(role)
            lines = [l.strip(" -0123456789.") for l in raw.splitlines()
                     if "?" in l]
            if len(lines) >= 4:
                questions = lines[:8]
        except Exception:
            pass
    return render(request, "dashboard/mock.html",
                  {"questions_json": json.dumps(questions), "role": role})


def chat_page(request):
    role = request.GET.get("role", "AI/ML Engineer")
    return render(request, "dashboard/chat.html", {"role": role})


def live_page(request):
    role = request.GET.get("role", "AI/ML Engineer")
    return render(request, "dashboard/live.html", {"role": role})


@require_POST
def chat_send(request):
    """Receives the conversation so far, returns the interviewer's next message."""
    try:
        body = json.loads(request.body.decode("utf-8"))
        messages = body.get("messages", [])
        role = body.get("role", "AI/ML Engineer")
        from agents import interview_prep as ip
        reply = ip.interview_chat(messages, role=role)
        return JsonResponse({"reply": reply})
    except Exception as e:
        return JsonResponse({"reply": f"(The AI was busy — please send that again.) [{str(e)[:50]}]"})


@require_POST
def mock_feedback(request):
    """Receives a transcript, returns AI feedback as JSON."""
    try:
        body = json.loads(request.body.decode("utf-8"))
        question = body.get("question", "")
        answer = body.get("answer", "")
        if not answer.strip():
            return JsonResponse({"feedback": "No speech was captured. Try speaking a bit louder, then stop."})
        from agents import interview_prep as ip
        fb = ip.answer_feedback(question, answer)
        return JsonResponse({"feedback": fb})
    except Exception as e:
        return JsonResponse({"feedback": f"The AI was busy — try again. ({str(e)[:60]})"})


