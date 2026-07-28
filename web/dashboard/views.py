# -*- coding: utf-8 -*-
"""JobPilot dashboard views — read/write the Supabase data via core.db."""

from django.shortcuts import render, redirect
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
    grade = request.GET.get("grade", "A")
    lane  = request.GET.get("lane", "")
    q = (_client().table("jobs")
         .select("id,title,company,location,portal,score,grade,lane,apply_url,match_reason,missing_skills,scam_flags")
         .order("score", desc=True).limit(100))
    if grade:
        q = q.eq("grade", grade)
    if lane:
        q = q.eq("lane", lane)
    rows = q.execute().data or []
    return render(request, "dashboard/jobs.html",
                  {"jobs": rows, "grade": grade, "lane": lane, "count": len(rows)})


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


# ── Grow & Practice (referrals + coding/study tracker) ─
def grow_page(request):
    referral = None
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "referral":
            from agents import referral_finder as rf
            company = request.POST.get("company", "").strip()
            role = request.POST.get("role", "").strip()
            if company:
                referral = rf.find_referral(company, role)
        elif action == "log":
            _add_practice(request)
            return redirect("grow")

    # practice stats
    entries, today_min, streak, totals = _practice_stats()
    return render(request, "dashboard/grow.html", {
        "referral": referral, "entries": entries,
        "today_min": today_min, "streak": streak, "totals": totals,
    })


def _add_practice(request):
    try:
        _client().table("practice_log").insert({
            "kind":    request.POST.get("kind", "leetcode"),
            "topic":   request.POST.get("topic", "")[:200],
            "count":   int(request.POST.get("count") or 0),
            "minutes": int(request.POST.get("minutes") or 0),
            "link":    request.POST.get("link", "")[:500],
            "notes":   request.POST.get("notes", "")[:500],
        }).execute()
    except Exception:
        pass


def _practice_stats():
    from datetime import date, timedelta
    try:
        rows = (_client().table("practice_log")
                .select("day,kind,topic,count,minutes,link")
                .order("id", desc=True).limit(60).execute().data or [])
    except Exception:
        return [], 0, 0, {}
    today = str(date.today())
    today_min = sum(r.get("minutes", 0) for r in rows if str(r.get("day")) == today)
    # streak: consecutive days with any entry
    days = {str(r.get("day")) for r in rows}
    streak, d = 0, date.today()
    while str(d) in days:
        streak += 1
        d -= timedelta(days=1)
    totals = {}
    for r in rows:
        k = r.get("kind", "other")
        totals[k] = totals.get(k, 0) + r.get("minutes", 0)
    return rows[:15], today_min, streak, totals
