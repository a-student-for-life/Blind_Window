"""Pilot driver: the 10 pilot events only (ANALYSIS_PLAN.md section 13).

    python -m study.run_pilot creds        # check accounts, prints no secrets
    python -m study.run_pilot events       # GloFAS reanalysis -> peak, onset, end per pilot event
    python -m study.run_pilot observed     # Earth Engine usable acquisitions -> observed blind window
    python -m study.run_pilot plans        # plan archive index + plan vs acquisition matching
    python -m study.run_pilot forecast     # GloFAS forecast + TIGGE cloud -> forecast vs baselines

Outputs go to pilot/out/ (committed, small JSON) and data/study/cache/ (not committed).
Every outcome stage calls study.guard first, so it cannot be pointed at main-set events before
the plan is approved.
"""
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import config as C
from . import creds, events, fetch, guard, observed

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pilot" / "out"
CACHE = ROOT / "data" / "study" / "cache"


def load_pilot():
    return json.loads(guard.PILOT.read_text(encoding="utf-8"))["events"]


def _save(name, obj):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")


def stage_creds():
    rows = creds.check()
    for name, ok, note in rows:
        print(f"{'OK ' if ok else 'NO '} {name:42s} {note}")
    return all(ok for _, ok, _ in rows)


def _series_from_nc(path, lat, lon):
    import xarray as xr
    ds = xr.open_dataset(path)
    var = next(v for v in ds.data_vars if "dis" in v.lower())
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    s = ds[var].sel({latn: lat, lonn: lon}, method="nearest")
    tname = next(c for c in s.coords if "time" in c)
    # EWDS labels a daily mean by the END of the day; shift back one day to the day it covers
    days = [(datetime.fromisoformat(str(t)[:19]) - timedelta(days=1)).date().isoformat() for t in s[tname].values]
    vals = [None if v != v else float(v) for v in s.values]
    return days, vals


def stage_events(thresholds):
    """thresholds: {event_id: rp5_m3s} read from the GloFAS v4 threshold file by the pilot."""
    out = []
    for ev in load_pilot():
        a, b = (date.fromisoformat(x) for x in ev["search_window"])
        days, vals = [], []
        for y in sorted({a.year, b.year}):
            target = CACHE / f"glofas_rea_{ev['id']}_{y}.nc"
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                fetch.retrieve_ewds(fetch.glofas_reanalysis_request(y, ev["lat"], ev["lon"]), target)
            d, v = _series_from_nc(target, ev["lat"], ev["lon"])
            days += d
            vals += v
        found = events.detect_events(days, vals, thresholds[ev["id"]])
        inside = [e for e in found if a <= e["peak_date"] <= b]
        out.append({"id": ev["id"], "threshold_rp5": thresholds[ev["id"]], "events": inside})
    _save("pilot_events_glofas.json", out)
    return out


def stage_observed(found):
    guard.require_outcome_access([e["id"] for e in found])
    fetch.init_ee()
    pilots = {p["id"]: p for p in load_pilot()}
    res = []
    for row in found:
        p = pilots[row["id"]]
        for ev in row["events"]:
            inst = events.instants(ev)
            acq = observed.ee_acquisitions(p["lat"], p["lon"], inst["onset"] - timedelta(days=10),
                                           inst["t0"] + timedelta(days=C.SEARCH_DAYS + 1))
            res.append({"id": row["id"], "peak_date": ev["peak_date"], **observed.blind_window(inst, acq),
                        "acquisitions": acq})
    _save("pilot_observed.json", res)
    return res


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "creds"
    if stage == "creds":
        sys.exit(0 if stage_creds() else 1)
    print(f"stage '{stage}' is run step by step in the pilot; see pilot/PILOT_NOTES.md")
