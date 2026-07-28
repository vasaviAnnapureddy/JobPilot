# -*- coding: utf-8 -*-
"""
BOSS AGENT — the supervisor (LangGraph).

The Boss:
  1. Checks YOUR master switch in the database.
     switch = 'stopped'  →  entire team sleeps. Nothing runs. Zero cost.
     switch = 'running'  →  workday begins.
  2. Sends Scout to find jobs.
  3. Sends Judge to grade them.
  4. Records the run result (success/failure) so the website
     and failure alerts always know what happened.

Stage 3 adds: Tailor → Applier → Outreach → Tracker nodes.

Run manually:   python run_agent.py
Run scheduled:  the cloud server calls run_agent.py daily.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import StateGraph, END
from core import db
from agents import scout, judge, tailor, applier, outreach, tracker


class PilotState(TypedDict):
    """The clipboard the Boss carries between agents."""
    switch_on: bool
    jobs_found: int
    jobs_graded: int
    grade_a: int
    suggestions: int
    lanes: dict
    drafts: int
    tracked: dict
    errors: list


# ── Nodes (each node = one agent doing its job) ──────

def check_switch(state: PilotState) -> PilotState:
    on = db.is_running()
    db.log("boss", f"Master switch: {'RUNNING — workday begins' if on else 'STOPPED — team sleeps'}")
    state["switch_on"] = on
    return state


def run_scout(state: PilotState) -> PilotState:
    try:
        state["jobs_found"] = scout.run()
    except Exception as e:
        db.log("boss", f"Scout crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"scout: {str(e)[:120]}")
    return state


def run_judge(state: PilotState) -> PilotState:
    try:
        graded, a_count = judge.run()
        state["jobs_graded"] = graded
        state["grade_a"] = a_count
    except Exception as e:
        db.log("boss", f"Judge crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"judge: {str(e)[:120]}")
    return state


def run_tailor(state: PilotState) -> PilotState:
    try:
        state["suggestions"] = tailor.run()
    except Exception as e:
        db.log("boss", f"Tailor crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"tailor: {str(e)[:120]}")
    return state


def run_applier(state: PilotState) -> PilotState:
    try:
        state["lanes"] = applier.run()
    except Exception as e:
        db.log("boss", f"Applier crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"applier: {str(e)[:120]}")
    return state


def run_outreach(state: PilotState) -> PilotState:
    try:
        state["drafts"] = outreach.run()
    except Exception as e:
        db.log("boss", f"Outreach crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"outreach: {str(e)[:120]}")
    return state


def run_tracker(state: PilotState) -> PilotState:
    try:
        state["tracked"] = tracker.run()
    except Exception as e:
        db.log("boss", f"Tracker crashed: {str(e)[:120]}", "ERROR")
        state["errors"].append(f"tracker: {str(e)[:120]}")
    return state


def wrap_up(state: PilotState) -> PilotState:
    status = "ok" if not state["errors"] else f"errors: {'; '.join(state['errors'])}"
    db.set_state("last_run_at", datetime.now().isoformat())
    db.set_state("last_run_status", status)
    db.log("boss", f"Run complete — found {state['jobs_found']}, graded {state['jobs_graded']}, "
                   f"Grade A: {state['grade_a']}, suggestions: {state.get('suggestions',0)}, "
                   f"drafts: {state.get('drafts',0)} | {status}")
    return state


# ── Routing (the Boss's decision) ─────────────────────

def route_after_switch(state: PilotState) -> str:
    return "scout" if state["switch_on"] else END


# ── Build the graph ───────────────────────────────────

def build_graph():
    g = StateGraph(PilotState)
    g.add_node("check_switch", check_switch)
    g.add_node("scout", run_scout)
    g.add_node("judge", run_judge)
    g.add_node("tailor", run_tailor)
    g.add_node("applier", run_applier)
    g.add_node("outreach", run_outreach)
    g.add_node("tracker", run_tracker)
    g.add_node("wrap_up", wrap_up)

    g.set_entry_point("check_switch")
    g.add_conditional_edges("check_switch", route_after_switch,
                            {"scout": "scout", END: END})
    g.add_edge("scout", "judge")
    g.add_edge("judge", "tailor")
    g.add_edge("tailor", "applier")
    g.add_edge("applier", "outreach")
    g.add_edge("outreach", "tracker")
    g.add_edge("tracker", "wrap_up")
    g.add_edge("wrap_up", END)
    return g.compile()


def run():
    graph = build_graph()
    initial: PilotState = {
        "switch_on": False, "jobs_found": 0, "jobs_graded": 0, "grade_a": 0,
        "suggestions": 0, "lanes": {}, "drafts": 0, "tracked": {}, "errors": [],
    }
    return graph.invoke(initial)
