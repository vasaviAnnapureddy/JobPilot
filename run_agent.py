# -*- coding: utf-8 -*-
"""
JobPilot — entry point.

  python run_agent.py            → one full agent workday
  python run_agent.py --start    → flip master switch ON
  python run_agent.py --stop     → flip master switch OFF
  python run_agent.py --status   → what's the current state?

(The website will do --start/--stop with a button in Stage 2.)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)

from core import db


def main():
    args = sys.argv[1:]

    if "--start" in args:
        db.set_state("master_switch", "running")
        print("✅ Master switch: RUNNING — the agent team is active.")
        return

    if "--stop" in args:
        db.set_state("master_switch", "stopped")
        print("🛑 Master switch: STOPPED — the agent team sleeps until you say start.")
        return

    if "--status" in args:
        print(f"Master switch : {db.get_state('master_switch', 'stopped')}")
        print(f"Last run      : {db.get_state('last_run_at', 'never')}")
        print(f"Last status   : {db.get_state('last_run_status', '-')}")
        return

    # Default: run one full workday
    from agents import boss
    result = boss.run()
    if not result["switch_on"]:
        print("\nSwitch is OFF. Turn on with:  python run_agent.py --start")


if __name__ == "__main__":
    main()
