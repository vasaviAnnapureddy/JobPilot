# -*- coding: utf-8 -*-
"""
PRACTICE LOG — one coding tracker that leads you.

You log each problem you solve (name, difficulty, topic, minutes). Stored in
a local file (data/practice_log.json) so it works IMMEDIATELY — no database,
no migration. The AI coach (agents/coding_coach.py) reads the summary below
to tell you what to solve next.
"""

import json
from datetime import date, datetime, timedelta
from core import config

LOG = config.BASE_DIR / "data" / "practice_log.json"


def _load():
    if LOG.exists():
        try:
            return json.loads(LOG.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save(rows):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def add(name="", difficulty="Easy", topic="", minutes=0, kind="leetcode", link=""):
    """Log one solved problem (or a study session if kind != leetcode)."""
    rows = _load()
    rows.insert(0, {
        "day": str(date.today()),
        "ts": datetime.now().strftime("%d %b, %I:%M %p"),
        "kind": kind, "name": name, "difficulty": difficulty,
        "topic": topic, "minutes": int(minutes or 0), "link": link,
    })
    _save(rows)


def entries(n=25):
    return _load()[:n]


def summary():
    """Everything the coach needs to guide you."""
    rows = _load()
    lc = [r for r in rows if r.get("kind", "leetcode") == "leetcode"]

    by_diff = {"Easy": 0, "Medium": 0, "Hard": 0}
    topics = {}
    for r in lc:
        d = r.get("difficulty", "Easy")
        by_diff[d] = by_diff.get(d, 0) + 1
        t = (r.get("topic") or "").strip().title()
        if t:
            topics[t] = topics.get(t, 0) + 1

    total_min = sum(r.get("minutes", 0) for r in rows)
    today = str(date.today())
    today_min = sum(r.get("minutes", 0) for r in rows if r.get("day") == today)

    days = {r.get("day") for r in rows}
    streak, d = 0, date.today()
    while str(d) in days:
        streak += 1
        d -= timedelta(days=1)

    return {
        "total":   len(lc),
        "easy":    by_diff["Easy"],
        "medium":  by_diff["Medium"],
        "hard":    by_diff["Hard"],
        "topics":  topics,                       # {topic: count}
        "hours":   round(total_min / 60, 1),
        "today_min": today_min,
        "streak":  streak,
        "recent":  [f"{r.get('name','?')} ({r.get('difficulty','')}, {r.get('topic','')})"
                    for r in lc[:8]],
    }
