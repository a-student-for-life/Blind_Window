"""Main run: every event in data/study/events_main.csv (made by `python -m study.scan`).

    python -m study.main                  # all stages for all main events, resumable
    python -m study.main --stage observed # one stage
    python -m study.main --only E00012 E00040
    python -m study.main --status         # how many events have finished each stage

Uses the same stages as the pilot (study/pilot.py), with results in data/study/out/<event>/.
RQ1 and RQ2 stages run for every main event; climatology, cloudclim and forecast only for the
forecast-test sample (data/study/rq3_sample.csv, DEVIATIONS.md #3), at the leads listed there.
The GloFAS stage is not downloaded again: the event comes from the scan.
"""
import argparse
import csv
import json
from datetime import date
from pathlib import Path

from . import config as C, events, pilot

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "study"
pilot.OUT = DATA / "out"
RQ3_STAGES = {"climatology", "cloudclim", "forecast"}


def main_events():
    with open(DATA / "events_main.csv", encoding="utf-8") as f:
        evs = list(csv.DictReader(f))
    rq3 = {}
    p = DATA / "rq3_sample.csv"
    if p.exists():
        with open(p, encoding="utf-8") as f:
            rq3 = {r["event_id"]: r for r in csv.DictReader(f)}
    out = []
    for e in evs:
        ev = {"id": e["event_id"], "name": e["point_id"], "lat": float(e["lat"]), "lon": float(e["lon"]),
              "row": e, "rq3": e["event_id"] in rq3}
        if ev["rq3"]:
            ev["leads"] = tuple(int(x) for x in rq3[e["event_id"]]["rq3_leads"].split(","))
        out.append(ev)
    return out


def write_glofas(ev):
    """glofas.json from the scan row, in the same shape the pilot's glofas stage writes."""
    if pilot.load(ev["id"], "glofas") is not None:
        return
    r = ev["row"]
    e = {"onset": date.fromisoformat(r["onset"]), "end": date.fromisoformat(r["end"]),
         "peak_date": date.fromisoformat(r["peak_date"]), "peak_m3s": float(r["peak_m3s"]), "n_above": int(r["n_above"])}
    pilot.save(ev["id"], "glofas", {"cell": [ev["lat"], ev["lon"]], "thresholds": {str(C.RETURN_PERIOD): float(r["threshold_m3s"])},
                                    "event": {**e, **events.instants(e)}, "source": "study.scan"})


def skip(ev, stage):
    if stage == "glofas":
        return None
    if stage in RQ3_STAGES and not ev["rq3"]:
        return "not in the forecast-test sample"
    return None


def status(evs):
    rows = {}
    for ev in evs:
        for st in pilot.STAGES:
            r = pilot.load(ev["id"], st)
            k = "missing" if r is None else ("skipped" if isinstance(r, dict) and r.get("skipped") else "done")
            rows.setdefault(st, {}).setdefault(k, 0)
            rows[st][k] += 1
        for st in pilot.STAGES:
            if (pilot.OUT / ev["id"] / f"{st}.error.txt").exists():
                rows[st]["errors"] = rows[st].get("errors", 0) + 1
    print(f"{len(evs)} main events, {sum(e['rq3'] for e in evs)} in the forecast-test sample")
    for st in pilot.STAGES:
        print(f"  {st:12s} " + "  ".join(f"{k} {v}" for k, v in sorted(rows.get(st, {}).items())))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--stage", choices=pilot.STAGES)
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()
    evs = main_events()
    if a.status:
        status(evs)
    else:
        for ev in evs:
            write_glofas(ev)
        pilot.RUNNERS["glofas"] = lambda ev: pilot.load(ev["id"], "glofas")
        pilot.run(a.only, a.stage, evs=evs, skip=skip)
        status(evs)
