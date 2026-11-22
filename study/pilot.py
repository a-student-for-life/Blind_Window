"""One-command, resumable pilot run (ANALYSIS_PLAN.md section 13).

    python -m study.pilot                 # every stage for every pilot event, skipping finished ones
    python -m study.pilot --only P01      # one event
    python -m study.pilot --stage observed
    python -m study.pilot --report        # rebuild pilot/out/PILOT_SUMMARY.md from saved results

Each stage writes pilot/out/<event>/<stage>.json when it succeeds, and the run skips it next time,
so the command can be stopped (Ctrl+C, laptop asleep) and started again at any point. Timings and
errors are appended to pilot/out/timings.jsonl. Large downloads stay in data/study/cache/.

Stages, in order (each needs the ones before it):
  glofas      GloFAS reanalysis around the search window -> peak, onset, end (5-year threshold)
  floodplain  floodplain point next to the river cell (Earth Engine, section 4)
  observed    usable S1/S2 acquisitions -> observed blind window (section 5)
  asf         Sentinel-1 RAW datatake records (RQ2 actual, baseline 2 history)
  plans       planned passes over the floodplain point from the archived ESA plans (section 6)
  climatology site climatology for baseline 3 (same month, other years, every 3rd day)
  forecast    GloFAS forecast + TIGGE cloud at leads 1, 3, 5 days -> forecast and baselines (section 7)
"""
import argparse
import json
import time
import traceback
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import baselines, config as C, events, fetch, guard, hindcast, observed, plan_index, plan_match

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pilot" / "out"
CACHE = ROOT / "data" / "study" / "cache"
UTC = timezone.utc
STAGES = ["glofas", "floodplain", "observed", "asf", "plans", "climatology", "forecast"]


class NotReady(RuntimeError):
    """A stage cannot run yet for a known reason (missing file, licence...). Not a bug."""


# ------------------------------------------------------------------ helpers

def _json_default(o):
    if isinstance(o, (datetime, date)):
        return o.isoformat()
    raise TypeError(type(o))


def _dt(s):
    if s is None or isinstance(s, datetime):
        return s
    return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(UTC)


def _d(s):
    return s if isinstance(s, date) and not isinstance(s, datetime) else date.fromisoformat(str(s)[:10])


def path(ev_id, stage):
    return OUT / ev_id / f"{stage}.json"


def load(ev_id, stage):
    p = path(ev_id, stage)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save(ev_id, stage, obj):
    p = path(ev_id, stage)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=1, default=_json_default), encoding="utf-8")
    tmp.replace(p)


def log_timing(row):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "timings.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=_json_default) + "\n")


def pilots():
    return json.loads(guard.PILOT.read_text(encoding="utf-8"))["events"]


def _acq_from_json(rows):
    return [{**a, "time": _dt(a["time"])} for a in rows]


# ------------------------------------------------------------------ stages

def stage_glofas(ev):
    """Peak, onset and end of the 5-year exceedance event inside the search window."""
    from .thresholds import rp_threshold
    a, b = (_d(x) for x in ev["search_window"])
    start, end = a - timedelta(days=60), b + timedelta(days=60)
    days, vals = [], []
    for y in range(start.year, end.year + 1):
        target = CACHE / f"glofas_rea_{ev['id']}_{y}.nc"
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            fetch.retrieve_ewds(fetch.glofas_reanalysis_request(y, ev["lat"], ev["lon"]), target)
        d, v, cell = series_from_nc(target, ev["lat"], ev["lon"])
        days += d
        vals += v
    keep = [(d, v) for d, v in zip(days, vals) if start <= _d(d) <= end]
    days, vals = [d for d, _ in keep], [v for _, v in keep]
    thr = {rp: rp_threshold(cell[0], cell[1], rp) for rp in (2, 5, 10)}
    found = events.detect_events(days, vals, thr[C.RETURN_PERIOD])
    inside = [e for e in found if a <= e["peak_date"] <= b]
    out = {"cell": cell, "thresholds": thr, "n_events_in_window": len(inside),
           "series": {"dates": days, "q": vals}}
    if inside:
        e = max(inside, key=lambda e: e["peak_m3s"])
        out["event"] = {**e, **events.instants(e)}
    else:
        out["event"] = None
        out["note"] = f"no {C.RETURN_PERIOD}-year exceedance in the search window"
    return out


def series_from_nc(path_, lat, lon):
    """Daily series at the cell nearest (lat, lon). EWDS labels a daily mean by the END of the
    24 h, so dates are shifted back one day to the day the mean covers."""
    import xarray as xr
    ds = xr.open_dataset(path_)
    var = next(v for v in ds.data_vars if "dis" in v.lower())
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    s = ds[var].sel({latn: lat, lonn: lon}, method="nearest")
    tname = next(c for c in s.dims if "time" in c)
    days = [(datetime.fromisoformat(str(t)[:19]) - timedelta(days=1)).date().isoformat() for t in s[tname].values]
    vals = [None if v != v else float(v) for v in s.values]
    cell = (float(s[latn]), float(s[lonn]))
    return days, vals, cell


def stage_floodplain(ev):
    from .floodplain import floodplain_point
    g = load(ev["id"], "glofas")
    fetch.init_ee()
    lat, lon = g["cell"]
    return floodplain_point(lat, lon)


def _need_event(ev):
    g = load(ev["id"], "glofas")
    if not g or not g.get("event"):
        raise NotReady("no GloFAS event for this pilot point")
    fp = load(ev["id"], "floodplain")
    if not fp or fp.get("lat") is None:
        raise NotReady("no floodplain point")
    e = g["event"]
    inst = {k: _dt(e[k]) for k in ("t0", "onset", "end")}
    return e, inst, fp


def stage_observed(ev):
    guard.require_outcome_access([ev["id"]])
    e, inst, fp = _need_event(ev)
    fetch.init_ee()
    acq = observed.ee_acquisitions(fp["lat"], fp["lon"], inst["onset"] - timedelta(days=10),
                                   inst["t0"] + timedelta(days=C.SEARCH_DAYS + 1))
    return {"acquisitions": acq, **observed.blind_window(inst, acq)}


def stage_asf(ev):
    guard.require_outcome_access([ev["id"]])
    e, inst, fp = _need_event(ev)
    start = inst["t0"] - timedelta(days=max(C.LEAD_DAYS_SECONDARY) + C.NEXT_S1_LOOKBACK_DAYS + 2)
    stop = inst["t0"] + timedelta(days=C.SEARCH_DAYS + 1)
    url, params = fetch.asf_s1_request(fp["lat"], fp["lon"], start, stop, level="RAW")
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=120) as r:
        feats = json.load(r)["features"]
    rows = []
    for f in feats:
        p = f["properties"]
        rows.append({"satellite": "S1" + p.get("platform", "Sentinel-1?")[-1].upper(),
                     "time": _dt(p["startTime"]), "stop": _dt(p.get("stopTime")),
                     "id": p.get("sceneName") or p.get("fileID")})
    rows.sort(key=lambda r: r["time"])
    # one row per datatake pass: RAW slices of the same pass are within minutes
    passes = []
    for r in rows:
        if passes and passes[-1]["satellite"] == r["satellite"] and r["time"] - passes[-1]["time"] <= timedelta(minutes=10):
            continue
        passes.append(r)
    return {"window": [start, stop], "n_products": len(rows), "passes": passes}


def stage_plans(ev):
    guard.require_outcome_access([ev["id"]])
    e, inst, fp = _need_event(ev)
    lo = inst["t0"] - timedelta(days=-C.RQ2_WINDOW[0] + 40)    # plans issued up to 40 days before
    hi = inst["t0"] + timedelta(days=C.RQ2_WINDOW[1])
    idx = [r for r in plan_index.index() if lo <= r["issued"] <= hi]
    if not idx:
        raise NotReady(f"no archived plans issued between {lo:%Y-%m-%d} and {hi:%Y-%m-%d} in "
                       f"{plan_index.ARCHIVE} (download the yearly SentiWiki ZIPs first)")
    from blindwindow import plans as bw_plans
    per_plan = []
    for r in idx:
        fps = plan_index.load(r)
        passes = bw_plans.passes_over(fps, fp["lat"], fp["lon"])
        per_plan.append({"satellite": r["satellite"], "issued": r["issued"], "valid_to": r["valid_to"],
                         "member": r["member"], "zip_mtime": r["zip_mtime"], "n_footprints": len(fps),
                         "passes": [{"satellite": p["satellite"], "time": p["time"], "kind": p["kind"]}
                                    for p in passes]})
    return {"plans": per_plan, "sats_present": sorted({p["satellite"] for p in per_plan})}


def planned_as_of(plans_json, t, lead_h=0):
    """Latest plan per satellite issued at least lead_h before t: its passes and its end."""
    plans = [{**p, "issued": _dt(p["issued"]), "valid_to": _dt(p["valid_to"])} for p in plans_json]
    chosen = plan_match.plan_available(plans, t, lead_h)
    passes, ends = [], {}
    for sat, p in chosen.items():
        ends[sat] = p["valid_to"]
        for q in p["passes"]:
            passes.append({"satellite": q["satellite"], "time": _dt(q["time"]), "kind": q["kind"],
                           "mode": None, "source": "planned"})
    return passes, ends


def rq2(ev):
    """Plan recall/precision over the RQ2 window, each pass judged by the plan issued >= 24 h before it."""
    pj, ob, asf = load(ev["id"], "plans"), load(ev["id"], "observed"), load(ev["id"], "asf")
    if not (pj and ob and asf):
        return None
    t0 = _dt(load(ev["id"], "glofas")["event"]["t0"])
    lo, hi = t0 + timedelta(days=C.RQ2_WINDOW[0]), t0 + timedelta(days=C.RQ2_WINDOW[1])
    plans = [{**p, "issued": _dt(p["issued"]), "valid_to": _dt(p["valid_to"])} for p in pj["plans"]]
    planned = {}
    for p in plans:
        for q in p["passes"]:
            tq = _dt(q["time"])
            if not lo <= tq <= hi or p["issued"] > tq - timedelta(hours=C.PLAN_LEAD_H):
                continue
            planned.setdefault((q["satellite"], tq.replace(second=0, microsecond=0)), {"satellite": q["satellite"], "time": tq})
    planned = list(planned.values())
    s1_actual = [{"satellite": a["satellite"], "time": _dt(a["time"])} for a in asf["passes"] if lo <= _dt(a["time"]) <= hi]
    usable = {(a["satellite"], _dt(a["time"]).replace(second=0, microsecond=0)): a["usable"] for a in ob["acquisitions"]}
    for a in s1_actual:
        a["usable"] = any(k[0] == a["satellite"] and abs(k[1] - a["time"]) <= timedelta(minutes=10) and v
                          for k, v in usable.items())
    s2_actual = [{"satellite": a["satellite"], "time": _dt(a["time"]), "usable": a["usable"]}
                 for a in ob["acquisitions"] if a["mission"] == "S2" and lo <= _dt(a["time"]) <= hi]
    out = {}
    for mission, actual in (("S1", s1_actual), ("S2", s2_actual)):
        c = plan_match.completeness([p for p in planned if p["satellite"].startswith(mission)], actual)
        out[mission] = {k: v for k, v in c.items() if k not in ("unplanned", "unacquired")}
        out[mission]["unplanned"] = [a["time"] for a in c["unplanned"]]
        out[mission]["unacquired"] = [p["time"] for p in c["unacquired"]]
    return out


def stage_climatology(ev):
    """Observed blind window (any mission) from every 3rd day of the same month in the other years."""
    guard.require_outcome_access([ev["id"]])
    e, inst, fp = _need_event(ev)
    fetch.init_ee()
    month, year = _d(e["peak_date"]).month, _d(e["peak_date"]).year
    rows = []
    y0, y1 = (int(PERIOD_Y) for PERIOD_Y in (C.PERIOD[0][:4], C.PERIOD[1][:4]))
    for y in range(y0, y1 + 1):
        if y == year:
            continue
        m_start = datetime(y, month, 1, tzinfo=UTC)
        m_end = (m_start + timedelta(days=32)).replace(day=1)
        acq = observed.ee_acquisitions(fp["lat"], fp["lon"], m_start, m_end + timedelta(days=C.SEARCH_DAYS + 1))
        d = m_start
        while d < m_end:
            inst_d = {"t0": d, "onset": d, "end": d}
            rows.append((d.date().isoformat(), observed.blind_window(inst_d, acq)["bw_any_h"]))
            d += timedelta(days=C.CLIMATOLOGY_STEP_DAYS)
    return {"month": month, "rows": rows}


def stage_forecast(ev):
    guard.require_outcome_access([ev["id"]])
    e, inst, fp = _need_event(ev)
    peak = _d(e["peak_date"])
    if peak < date.fromisoformat(C.RQ3_START):
        return {"skipped": "peak before the GloFAS forecast archive (RQ1/RQ2 only)"}
    pj, asf, clim, ob = (load(ev["id"], s) for s in ("plans", "asf", "climatology", "observed"))
    if not (pj and asf and clim and ob):
        raise NotReady("needs plans, asf, climatology and observed first")
    g = load(ev["id"], "glofas")
    t_obs = _dt(ob["first_usable_time"]) or inst["t0"] + timedelta(hours=C.CENSOR_H)
    site = [(_d(d), bw) for d, bw in clim["rows"]]
    leads = {}
    for L in (C.LEAD_DAYS_MAIN,) + tuple(C.LEAD_DAYS_SECONDARY):
        tau = hindcast.issue_time(peak, L)
        fc_path = CACHE / f"glofas_fc_{ev['id']}_{tau:%Y%m%d}.nc"
        if not fc_path.exists():
            fetch.retrieve_ewds(fetch.glofas_forecast_request(tau.date(), g["cell"][0], g["cell"][1]), fc_path)
        fc_dates, members = forecast_members(fc_path, g["cell"][0], g["cell"][1], tau)
        pred_peak = hindcast.predicted_peak(fc_dates, members)
        cloud = tigge_cloud(ev, tau, fp["lat"], fp["lon"])
        passes, ends = planned_as_of(pj["plans"], tau)
        f = hindcast.forecast(tau, pred_peak, passes, ends, cloud)
        past_s1 = [{"satellite": a["satellite"], "time": _dt(a["time"])} for a in asf["passes"]]
        preds = {
            "blind_window": f["t_hat"],
            "next_any_pass": baselines.next_any_pass(pred_peak, hindcast.bw_plans.project(passes, ends, tau + timedelta(days=60))),
            "next_s1_pass": baselines.next_s1_projection(pred_peak, past_s1, tau),
            "climatology": baselines.climatology(pred_peak, site, peak.year, _d(pred_peak).month),
        }
        err = {k: (None if v is None else round(min(abs((v - t_obs).total_seconds()) / 3600, C.CENSOR_H), 1))
               for k, v in preds.items()}
        leads[str(L)] = {"tau": tau, "pred_peak_date": pred_peak, "obs_peak_date": e["peak_date"],
                         "predictions": preds, "abs_err_h": err, "n_cloud_steps": len(cloud)}
    return {"t_obs": t_obs, "leads": leads}


def forecast_members(path_, lat, lon, tau):
    """Per-member daily series from a GloFAS forecast file. Returns (dates, [member series])."""
    import xarray as xr
    ds = xr.open_dataset(path_)
    var = next(v for v in ds.data_vars if "dis" in v.lower())
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    s = ds[var].sel({latn: lat, lonn: lon}, method="nearest")
    step = next(c for c in s.dims if "step" in c or "lead" in c or c == "valid_time")
    num = next((c for c in s.dims if c in ("number", "realization", "member")), None)
    steps = s[step].values
    dates = []
    for st in steps:
        hours = float(st / 3.6e12) if hasattr(st, "dtype") and "timedelta" in str(st.dtype) else float(st)
        dates.append(((tau + timedelta(hours=hours)) - timedelta(days=1)).date().isoformat())
    if num is None:
        return dates, [[None if v != v else float(v) for v in s.values]]
    members = [[None if v != v else float(v) for v in s.isel({num: i}).values] for i in range(s.sizes[num])]
    return dates, members


def tigge_cloud(ev, tau, lat, lon):
    """[(valid_time, tcc %)] ensemble mean at the point from the TIGGE forecast issued at tau."""
    target = CACHE / f"tigge_{ev['id']}_{tau:%Y%m%d}.grib"
    if not target.exists():
        fetch.retrieve_tigge_ecds(tau.date(), lat, lon, target)
    return fetch.tigge_point_series(target, lat, lon, tau)


RUNNERS = {"glofas": stage_glofas, "floodplain": stage_floodplain, "observed": stage_observed,
           "asf": stage_asf, "plans": stage_plans, "climatology": stage_climatology,
           "forecast": stage_forecast}


# ------------------------------------------------------------------ driver and report

def run(only=None, stage=None):
    for ev in pilots():
        if only and ev["id"] not in only:
            continue
        for st in STAGES:
            if stage and st != stage:
                continue
            if load(ev["id"], st) is not None:
                continue
            t0 = time.time()
            try:
                res = RUNNERS[st](ev)
                save(ev["id"], st, res)
                status, msg = "ok", ""
            except NotReady as e:
                status, msg = "not_ready", str(e)
            except KeyboardInterrupt:
                raise
            except Exception as e:
                status, msg = "error", f"{type(e).__name__}: {e}"
                (OUT / ev["id"]).mkdir(parents=True, exist_ok=True)
                (OUT / ev["id"] / f"{st}.error.txt").write_text(traceback.format_exc(), encoding="utf-8")
            secs = round(time.time() - t0, 1)
            log_timing({"event": ev["id"], "stage": st, "status": status, "seconds": secs,
                        "at": datetime.now(UTC), "msg": msg[:300]})
            print(f"{ev['id']:4s} {st:12s} {status:9s} {secs:7.1f}s {msg[:120]}", flush=True)
            if status != "ok":
                break               # later stages of this event depend on this one
    report()


def report():
    lines = ["# Pilot summary (generated by `python -m study.pilot --report`)", "",
             "| Event | Peak | BW any (h) | BW S1 (h) | BW S2 (h) | Missed | S1 plan recall | Err BW / any / S1 / clim (h), L=3 |",
             "|---|---|---|---|---|---|---|---|"]
    for ev in pilots():
        g, ob, fc = load(ev["id"], "glofas"), load(ev["id"], "observed"), load(ev["id"], "forecast")
        r = rq2(ev)
        peak = g["event"]["peak_date"] if g and g.get("event") else "-"
        if ob:
            bw = [ob["bw_any_h"], ob["bw_s1_h"], ob["bw_s2_h"], "yes" if ob["missed"] else "no"]
        else:
            bw = ["-"] * 4
        rec = f"{r['S1']['recall']:.2f}" if r and r["S1"]["recall"] is not None else "-"
        err = "-"
        if fc and "leads" in fc and str(C.LEAD_DAYS_MAIN) in fc["leads"]:
            e = fc["leads"][str(C.LEAD_DAYS_MAIN)]["abs_err_h"]
            err = " / ".join(str(e[k]) for k in ("blind_window", "next_any_pass", "next_s1_pass", "climatology"))
        elif fc and "skipped" in fc:
            err = "n/a (before forecast archive)"
        lines.append(f"| {ev['id']} {ev['name']} | {peak} | " + " | ".join(str(x) for x in bw) + f" | {rec} | {err} |")
    lines += ["", "## Time per stage", "", "| Stage | Runs | Median s | Max s | Errors / not ready |", "|---|---|---|---|---|"]
    tf = OUT / "timings.jsonl"
    rows = [json.loads(l) for l in tf.read_text(encoding="utf-8").splitlines()] if tf.exists() else []
    for st in STAGES:
        ok = sorted(r["seconds"] for r in rows if r["stage"] == st and r["status"] == "ok")
        bad = sum(1 for r in rows if r["stage"] == st and r["status"] != "ok")
        med = ok[len(ok) // 2] if ok else "-"
        lines.append(f"| {st} | {len(ok)} | {med} | {ok[-1] if ok else '-'} | {bad} |")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "PILOT_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--stage", choices=STAGES)
    ap.add_argument("--report", action="store_true")
    a = ap.parse_args()
    if a.report:
        report()
    else:
        run(a.only, a.stage)
