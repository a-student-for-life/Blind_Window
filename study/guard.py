"""Refuse to pull main-set outcomes before the analysis plan is approved.

Outcome data = satellite acquisitions, pixel checks, plans matched to events, cloud forecasts.
The event list itself (from GloFAS discharge) is not outcome data.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "ANALYSIS_PLAN.md"
PILOT = ROOT / "pilot" / "pilot_events.json"
APPROVED_RE = re.compile(r"^Status: \*\*approved by Janice on [0-9]{1,2} \w+ 20[0-9]{2}", re.M)


class PlanNotApproved(RuntimeError):
    pass


def plan_approved(text=None):
    text = PLAN.read_text(encoding="utf-8") if text is None else text
    return bool(APPROVED_RE.search(text))


def pilot_ids():
    return {e["id"] for e in json.loads(PILOT.read_text(encoding="utf-8"))["events"]}


def require_outcome_access(event_ids, plan_text=None):
    """Raise unless every id is a pilot event or the plan is approved."""
    ids = set(event_ids)
    if ids <= pilot_ids():
        return "pilot"
    if plan_approved(plan_text):
        return "main"
    extra = sorted(ids - pilot_ids())[:5]
    raise PlanNotApproved(
        f"ANALYSIS_PLAN.md is not approved yet; refusing outcome data for non-pilot events {extra}...")
