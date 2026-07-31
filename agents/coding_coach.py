# -*- coding: utf-8 -*-
"""
CODING COACH — the brain that leads your LeetCode practice.

Two modes:
  1. next_for_me()        -> based on YOUR history + level, what to solve next
  2. for_company(company) -> what that company focuses on + a plan for you

It reads your practice summary (core/practice.py) so advice fits your level:
few problems solved -> start Easy; strong on arrays -> move to next topic, etc.
"""

from core import llm, db, practice


def _profile_line():
    s = practice.summary()
    topics = ", ".join(f"{t} x{c}" for t, c in sorted(s["topics"].items(), key=lambda x: -x[1])) or "none yet"
    recent = "; ".join(s["recent"]) or "nothing logged yet"
    return s, (
        f"Total solved: {s['total']} (Easy {s['easy']}, Medium {s['medium']}, Hard {s['hard']}). "
        f"Topics practiced: {topics}. Streak: {s['streak']} days. Recent: {recent}."
    )


def next_for_me():
    s, prof = _profile_line()
    beginner = s["total"] < 10
    prompt = f"""You are a kind, practical coding-interview coach for Vasavi, a fresher targeting
AI/ML, Data Science and Data Analyst roles in India.

HER LEETCODE PROGRESS: {prof}
Is she a beginner? {"YES - very few solved, keep it Easy." if beginner else "No, she has some practice."}

Reply in simple English, short bullet points (10th-grade level):
1. WHERE YOU STAND - one honest line.
2. FOCUS NEXT - 2 topics to work on now (right for her level; if beginner, Easy arrays/strings/hashing). Say why briefly.
3. SOLVE TOMORROW - name 3 SPECIFIC real LeetCode problems by their exact names (Easy if she is a beginner), each with its difficulty. Use well-known problems she can search on leetcode.com.
4. ONE TIP - a habit to improve.
Be encouraging."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("coding", m, "WARN"))
    return ans


def for_company(company):
    s, prof = _profile_line()
    prompt = f"""You are a coding-interview coach. Vasavi (fresher, AI/ML & Data Science) is
targeting this company: {company}.

HER LEETCODE PROGRESS: {prof}

Reply in simple English, short bullet points:
1. WHAT {company} FOCUSES ON — the coding topics and difficulty they usually ask freshers (if unsure, say "commonly" and give the typical fresher pattern; do not invent exact questions).
2. YOUR GAP — comparing her progress to what they want, what to practice more.
3. A 1-WEEK PLAN - day by day, which topic + name 1-2 SPECIFIC real LeetCode problems by name each day (matched to her level).
4. BEYOND CODING - 1 line on what else matters for {company} (projects, communication).
Use real, well-known LeetCode problem names. Keep it realistic and honest. If unsure about the company's exact style, say so."""
    ans = llm.ask(prompt, log_fn=lambda m: db.log("coding", m, "WARN"))
    return ans
