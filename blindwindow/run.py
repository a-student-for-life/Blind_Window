"""Build today's outlook snapshot and render the page.

    python -m blindwindow.run            # live run (needs internet)
    python -m blindwindow.run --render   # re-render page from the latest saved snapshot (no internet)
    python -m blindwindow.run --resnap   # redo river snapping
"""
import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from . import cloud, flood, http, plans, predictor, render
from .config import FORECAST_DAYS, RIVER_POINTS

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def _iso(o):
    if isinstance(o, datetime):
        return o.isoformat()
    raise TypeError(type(o))


def run_point(point, footprints, plan_end, now, resnap):
    rec = {"id": point["id"], "name": point["name"], "seed": [point["lat"], point["lon"]], "errors": []}
    snap = flood.snap(point, refresh=resnap)
    rec["snap"] = snap
    if snap.get("status") != "ok":
        rec["errors"].append(f"snap {snap.get('status')}: main river not confirmed; forecast not shown")
        return rec
    cell = (snap["lat"], snap["lon"])

    fc = flood.forecast(*cell)
    rec["forecast"] = fc
    if "peak_date" not in fc:
        rec["errors"].append("forecast returned no discharge values")
        return rec

    until = now + timedelta(days=FORECAST_DAYS + 2)
    passes = plans.passes_over(footprints, *cell)
    passes = plans.project(passes, plan_end, until)
    try:
        clouds = cloud.hourly_cloud(*cell)
    except Exception as e:
        clouds = {}
        rec["errors"].append(f"cloud forecast failed: {e!r}")
    lookup = lambda t: cloud.at(clouds, t)

    res = predictor.predict(fc["peak_date"], passes, lookup)
    rec["result"] = res
    rec["all_passes"] = [{**p, "cloud_pct": lookup(p["time"]) if p["kind"] == "optical" else None} for p in passes]
    windows = predictor.member_windows(fc.get("members", []), passes, lookup)
    rec["member_windows"] = windows
    rec["member_spread_h"] = predictor.spread([w["blind_window_h"] for w in windows])
    rec["members_beyond_horizon"] = sum(w["blind_window_h"] is None for w in windows)
    rec["brief"] = predictor.draft_brief(point, cell, res, now)
    return rec


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--render", action="store_true", help="only re-render from outputs/latest.json")
    ap.add_argument("--resnap", action="store_true")
    ap.add_argument("--only", help="comma-separated point ids")
    a = ap.parse_args(argv)
    OUT.mkdir(exist_ok=True)

    if a.render:
        snap = json.loads((OUT / "latest.json").read_text()) if (OUT / "latest.json").exists() else None
        page = render.write(snap, OUT / "blind_window.html")
        print("rendered", page)
        return

    now = datetime.now(timezone.utc).replace(microsecond=0)
    print("issue time", now.isoformat())
    try:
        footprints, plan_meta, plan_end = plans.load_footprints(now)
    except Exception as e:
        footprints, plan_meta, plan_end = [], [{"error": repr(e)}], {}
    print(f"plans: {len(footprints)} footprints from", [m.get("satellite") for m in plan_meta])

    points = [p for p in RIVER_POINTS if not a.only or p["id"] in a.only.split(",")]
    records = []
    for p in points:
        try:
            r = run_point(p, footprints, plan_end, now, a.resnap)
        except Exception as e:
            r = {"id": p["id"], "name": p["name"], "errors": [f"failed: {e!r}"]}
        print(f"- {p['id']}: errors={r['errors']}")
        records.append(r)

    snapshot = {"issued_at": now, "plans": plan_meta, "points": records,
                "requests": http.LOG[-500:]}
    text = json.dumps(snapshot, default=_iso, indent=1)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    (OUT / f"snapshot_{stamp}.json").write_text(text)
    (OUT / "latest.json").write_text(text)

    # prospective log: today's predictions, to be scored once the future arrives
    with (OUT / "prospective_log.jsonl").open("a") as f:
        for r in records:
            res = r.get("result")
            if not res:
                continue
            aw = res["cloud_aware"]
            f.write(json.dumps({"issued_at": now.isoformat(), "point": r["id"],
                                "cell": [r["snap"]["lat"], r["snap"]["lon"]],
                                "predicted_peak_date": r["forecast"]["peak_date"],
                                "predicted_first_usable": aw["time"].isoformat() if aw else None,
                                "predicted_satellite": aw["satellite"] if aw else None,
                                "blind_window_h": res["blind_window_h"]}) + "\n")

    page = render.write(json.loads(text), OUT / "blind_window.html")
    print("wrote", page)


if __name__ == "__main__":
    sys.exit(main())
