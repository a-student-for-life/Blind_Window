"""Main event list (ANALYSIS_PLAN.md section 3): river points, GloFAS reanalysis, 5-year events,
exclusions, the 800 cap and the forecast-test sample (DEVIATIONS.md #3). GloFAS data only: no
satellite outcome is touched here, so it may run before any outcome stage.

    python -m study.scan points      # river points from the GloFAS network files (data/study/aux/)
    python -m study.scan download    # reanalysis by 10-degree tile and year, 2 at a time, resumable
    python -m study.scan events      # events, exclusions, cap, RQ3 sample -> data/study/*.csv
    python -m study.scan             # all three in order

Needs in data/study/aux/ (CEMS GloFAS v4 auxiliary data, saved by hand, never committed): the
upstream-area file (name containing "uparea"), the drainage-direction file ("ldd"), optionally
lake and reservoir masks ("lake", "reservoir"), and the return-period files (thresholds.py).
Each step writes its result and the next run skips finished work, so it can be stopped any time.
"""
import argparse
import csv
import json
import math
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config as C, events, fetch

ROOT = Path(__file__).resolve().parent.parent
AUX = ROOT / "data" / "study" / "aux"
CACHE = ROOT / "data" / "study" / "cache"
SCAN = ROOT / "data" / "study" / "scan"          # per-tile series (not committed)
OUT = ROOT / "data" / "study"                    # committed CSVs
TILE_DEG = 10
WORKERS = 2                                      # ECMWF warns against flooding the queue

# FIPS 10-4 codes in USDOS/LSIB_SIMPLE/2017 for the study countries (config.COUNTRIES, ISO3)
LSIB = {"IN": "IND", "PK": "PAK", "BG": "BGD", "NP": "NPL", "BT": "BTN", "CE": "LKA", "BM": "MMR",
        "TH": "THA", "LA": "LAO", "CB": "KHM", "VM": "VNM", "MY": "MYS", "ID": "IDN", "RP": "PHL",
        "TT": "TLS", "BX": "BRN"}


# ------------------------------------------------------------------ pure helpers (tested)

LDD_STEP = {1: (-1, -1), 2: (-1, 0), 3: (-1, 1), 4: (0, -1), 6: (0, 1), 7: (1, -1), 8: (1, 0), 9: (1, 1)}


def outlets(ldd, lat_up):
    """Outlet cell of every cell, following the PCRaster drainage directions (5 = pit).
    ldd: 2-D list/array [row][col]; lat_up: +1 if latitude increases with the row index, else -1.
    Returns a dict {(row, col): (row, col) of the outlet} for every non-missing cell. A path that
    leaves the grid ends at its last cell inside it."""
    nr, nc = len(ldd), len(ldd[0])
    out = {}
    for r0 in range(nr):
        for c0 in range(nc):
            if (r0, c0) in out or not _valid(ldd[r0][c0]):
                continue
            path, on_path, r, c = [], set(), r0, c0
            while True:
                if (r, c) in out:
                    end = out[(r, c)]
                    break
                path.append((r, c))
                on_path.add((r, c))
                v = int(ldd[r][c])
                if v not in LDD_STEP:
                    end = (r, c)
                    break
                dr, dc = LDD_STEP[v]
                rn, cn = r + dr * lat_up, c + dc
                if not (0 <= rn < nr and 0 <= cn < nc) or not _valid(ldd[rn][cn]) or (rn, cn) in on_path:
                    end = (r, c)
                    break
                r, c = rn, cn
            for p in path:
                out[p] = end
    return out


def _valid(v):
    return v is not None and v == v and int(v) in range(1, 10)


def tiles_for(points, deg=TILE_DEG):
    """Group points by tile; tile key 'lat0_lon0' (south-west corner)."""
    t = {}
    for p in points:
        k = f"{math.floor(p['lat'] / deg) * deg}_{math.floor(p['lon'] / deg) * deg}"
        t.setdefault(k, []).append(p)
    return t


def cap_sample(evs, cap, seed):
    """Section 3 cap: seeded random sample stratified by year (proportional, largest remainder)."""
    import random
    if len(evs) <= cap:
        return list(evs)
    rng = random.Random(seed)
    by_year = {}
    for e in sorted(evs, key=lambda e: e["event_id"]):
        by_year.setdefault(str(e["peak_date"])[:4], []).append(e)
    for v in by_year.values():
        rng.shuffle(v)
    quota = {y: cap * len(v) / len(evs) for y, v in by_year.items()}
    take = {y: int(q) for y, q in quota.items()}
    for y in sorted(quota, key=lambda y: (-(quota[y] - take[y]), y))[: cap - sum(take.values())]:
        take[y] += 1
    keep = [e for y, v in by_year.items() for e in v[: take[y]]]
    return sorted(keep, key=lambda e: e["event_id"])


# ------------------------------------------------------------------ step 1: river points

def _aux(word):
    f = sorted(p for p in AUX.glob("*.nc") if word in p.name.lower())
    return f[0] if f else None


def step_points():
    target = OUT / "points.csv"
    if target.exists():
        print(f"points: {target} exists, skipping")
        return
    import numpy as np
    import xarray as xr
    lon0, lat0, lon1, lat1 = C.BBOX
    up_f, ldd_f = _aux("uparea"), _aux("ldd")
    if not (up_f and ldd_f):
        raise SystemExit(f"Save the GloFAS v4 'uparea' and 'ldd' NetCDF files into {AUX} first")

    def crop(f):
        ds = xr.open_dataset(f)
        latn = "latitude" if "latitude" in ds.coords else "lat"
        lonn = "longitude" if "longitude" in ds.coords else "lon"
        da = ds[next(v for v in ds.data_vars if ds[v].ndim >= 2)]
        lats = ds[latn].values
        sl = slice(lat1, lat0) if lats[0] > lats[-1] else slice(lat0, lat1)
        da = da.sel({latn: sl, lonn: slice(lon0, lon1)}).squeeze()
        return da, latn, lonn

    up, latn, lonn = crop(up_f)
    ldd, _, _ = crop(ldd_f)
    upv = up.values.astype("float64")
    if np.nanmax(upv) > 1e9:                       # m2 -> km2
        upv = upv / 1e6
    lats, lons = up[latn].values, up[lonn].values
    lat_up = 1 if lats[1] > lats[0] else -1
    lake = np.zeros(upv.shape, bool)
    for w in ("lake", "reservoir"):
        f = _aux(w)
        if f:
            m, _, _ = crop(f)
            lake |= np.nan_to_num(m.values) > 0
    big = upv >= C.MIN_UPSTREAM_KM2
    print(f"points: {int(big.sum())} GloFAS cells with upstream area >= {C.MIN_UPSTREAM_KM2} km2; tracing outlets")
    lv = ldd.values
    sub = [[(lv[r][c] if big[r][c] else None) for c in range(lv.shape[1])] for r in range(lv.shape[0])]
    outl = outlets(sub, lat_up)
    cells = [{"lat": round(float(lats[r]), 4), "lon": round(float(lons[c]), 4), "upstream_km2": round(float(upv[r, c]), 1),
              "outlet": f"{outl[(r, c)][0]}_{outl[(r, c)][1]}", "lake": bool(lake[r, c])}
             for r, c in zip(*np.nonzero(big)) if (r, c) in outl]
    kept = events.thin_points(cells)
    print(f"points: {len(kept)} after thinning ({C.THIN_KM} km, same outlet) and dropping lakes/reservoirs")
    kept = _country_and_basin(kept)
    kept = [p for p in kept if p["country"] in C.COUNTRIES]
    for i, p in enumerate(kept):
        p["point_id"] = f"R{i:05d}"
    _write_csv(target, kept, ["point_id", "lat", "lon", "upstream_km2", "outlet", "country", "basin"])
    print(f"points: {len(kept)} river points inside the study countries -> {target}")


def _country_and_basin(pts, chunk=500):
    """Country (LSIB, mapped to ISO3) and HydroBASINS level-4 id for each point, via Earth Engine."""
    ee = fetch.init_ee()
    countries = ee.FeatureCollection("USDOS/LSIB_SIMPLE/2017")
    basins = ee.FeatureCollection("WWF/HydroSHEDS/v1/Basins/hybas_4")
    out = []
    for k in range(0, len(pts), chunk):
        part = pts[k:k + chunk]
        fc = ee.FeatureCollection([ee.Feature(ee.Geometry.Point([p["lon"], p["lat"]]), {"i": i})
                                   for i, p in enumerate(part)])
        j1 = ee.Join.saveFirst("c").apply(fc, countries, ee.Filter.intersects(leftField=".geo", rightField=".geo"))
        j2 = ee.Join.saveFirst("b").apply(j1, basins, ee.Filter.intersects(leftField=".geo", rightField=".geo"))
        rows = ee.FeatureCollection(j2).map(lambda f: ee.Feature(None, {
            "i": f.get("i"),
            "cc": ee.Algorithms.If(f.get("c"), ee.Feature(f.get("c")).get("country_co"), ""),
            "hb": ee.Algorithms.If(f.get("b"), ee.Feature(f.get("b")).get("HYBAS_ID"), -1)})).getInfo()["features"]
        for r in rows:
            pr = r["properties"]
            p = dict(part[int(pr["i"])])
            p["country"] = LSIB.get(pr.get("cc") or "", pr.get("cc") or "")
            p["basin"] = int(pr.get("hb") or -1)
            out.append(p)
    return out


# ------------------------------------------------------------------ step 2: reanalysis by tile

def _tile_request(key, year):
    lat0, lon0 = (int(x) for x in key.split("_"))
    ds, req = fetch.glofas_reanalysis_request(year, 0, 0)
    req["area"] = [lat0 + TILE_DEG, lon0, lat0, lon0 + TILE_DEG]
    return ds, req


def _extract(nc, pts, year, target):
    """Daily series (date shifted back one day, as in pilot.series_from_nc) at each point's cell."""
    import numpy as np
    import xarray as xr
    ds = xr.open_dataset(nc)
    var = next(v for v in ds.data_vars if "dis" in v.lower())
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    tname = next(c for c in ds[var].dims if "time" in c)
    days = [(datetime.fromisoformat(str(t)[:19]) - timedelta(days=1)).date().isoformat() for t in ds[tname].values]
    sel = ds[var].sel({latn: xr.DataArray([p["lat"] for p in pts], dims="p"),
                       lonn: xr.DataArray([p["lon"] for p in pts], dims="p")}, method="nearest")
    vals = sel.transpose("p", tname).values.astype("float32")
    np.savez_compressed(target, ids=np.array([p["point_id"] for p in pts]), days=np.array(days), q=vals)
    ds.close()


def tile_order(tiles, scan_dir=None):
    """Tiles in a seeded random order, all years of a tile together, so the tiles finished by any
    cut-off date are a random sample of the region with complete records (DEVIATIONS.md #7).
    Tiles that already have a finished year go first, so no started tile is left half done."""
    import random
    scan_dir = scan_dir or SCAN
    keys = sorted(tiles)
    random.Random(C.SEED).shuffle(keys)
    started = [k for k in keys if any(scan_dir.glob(f"{k}_*.npz"))]
    return [(k, tiles[k]) for k in started + [k for k in keys if k not in started]]


def complete_tiles(tiles, scan_dir=None):
    """Tiles with every year of the study period downloaded."""
    scan_dir = scan_dir or SCAN
    y0, y1 = int(C.PERIOD[0][:4]), int(C.PERIOD[1][:4])
    return {k for k in tiles if all((scan_dir / f"{k}_{y}.npz").exists() for y in range(y0, y1 + 1))}


def step_download(keep_raw=False):
    pts = _read_points()
    jobs = []
    y0, y1 = int(C.PERIOD[0][:4]), int(C.PERIOD[1][:4])
    for key, tp in tile_order(tiles_for(pts)):
        for y in range(y0, y1 + 1):                # edge events are excluded anyway (EDGE_DAYS)
            if not (SCAN / f"{key}_{y}.npz").exists():
                jobs.append((key, y, tp))
    print(f"download: {len(jobs)} tile-years to fetch ({len(tiles_for(pts))} tiles), {WORKERS} at a time")
    SCAN.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)

    def one(job):
        key, y, tp = job
        nc = CACHE / f"scan_{key}_{y}.nc"
        t = time.time()
        try:
            if not nc.exists():
                fetch.retrieve_ewds(_tile_request(key, y), nc)
            _extract(nc, tp, y, SCAN / f"{key}_{y}.npz")
            if not keep_raw:
                nc.unlink()
            msg = "ok"
        except Exception as e:                      # logged; the next run retries it
            msg = f"error {type(e).__name__}: {str(e)[:200]}"
        line = {"tile": key, "year": y, "seconds": round(time.time() - t), "status": msg, "at": datetime.now().isoformat()}
        with open(SCAN / "download_log.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")
        print(f"{key} {y}: {msg} ({line['seconds']} s)", flush=True)

    with ThreadPoolExecutor(WORKERS) as ex:
        list(ex.map(one, jobs))


# ------------------------------------------------------------------ step 3: events

def step_events():
    import numpy as np
    from .thresholds import rp_threshold
    pts = {p["point_id"]: p for p in _read_points()}
    tiles = tiles_for(list(pts.values()))
    done = complete_tiles(tiles)
    if len(done) < len(tiles):
        print(f"events: only {len(done)} of {len(tiles)} tiles complete; using those (random tile order, DEVIATIONS.md #7)")
    parts = {}
    for f in sorted(SCAN.glob("*.npz")):
        if f.stem.rsplit("_", 1)[0] not in done:
            continue
        z = np.load(f)
        for pid, row in zip(z["ids"], z["q"]):
            parts.setdefault(str(pid), []).append((z["days"], row))
    series = {}
    for pid, lst in parts.items():
        d = np.concatenate([a for a, _ in lst])
        q = np.concatenate([b for _, b in lst])
        o = np.argsort(d, kind="stable")
        series[pid] = (d[o].tolist(), [None if v != v else float(v) for v in q[o]])
    missing = [pid for pid in pts if pid not in series]
    if missing:
        print(f"events: WARNING {len(missing)} points have no series yet (run download again)")
    pilots = _pilot_refs()
    p_lo = (date.fromisoformat(C.PERIOD[0]) + timedelta(days=C.EDGE_DAYS)).isoformat()
    p_hi = (date.fromisoformat(C.PERIOD[1]) - timedelta(days=C.EDGE_DAYS)).isoformat()
    allev, counts = [], {"edge": 0, "pilot": 0, "no_threshold": 0}
    for pid, s in sorted(series.items()):
        p = pts.get(pid)
        if not p:
            continue
        thr = rp_threshold(p["lat"], p["lon"], C.RETURN_PERIOD)
        if thr is None:
            counts["no_threshold"] += 1
            continue
        days, qs = s
        for e in events.detect_events(days, qs, thr):
            pk = str(e["peak_date"])[:10]
            if not (C.PERIOD[0] <= pk <= C.PERIOD[1]):
                continue
            row = {"point_id": pid, "lat": p["lat"], "lon": p["lon"], "country": p["country"],
                   "basin": str(p["basin"]) if p["basin"] != -1 else "outlet_" + p["outlet"],   # no basin: own river
                   "upstream_km2": p["upstream_km2"], "threshold_m3s": round(thr, 1),
                   "onset": str(e["onset"])[:10], "peak_date": pk, "end": str(e["end"])[:10],
                   "peak_m3s": round(e["peak_m3s"], 1), "n_above": e["n_above"]}
            if not (p_lo <= pk <= p_hi):
                counts["edge"] += 1
                continue
            if events.near_pilot(row, pilots):
                counts["pilot"] += 1
                continue
            allev.append(row)
    allev.sort(key=lambda e: (e["peak_date"], e["point_id"]))
    for i, e in enumerate(allev):
        e["event_id"] = f"E{i:05d}"
    for e, ep in zip(allev, events.episodes(allev)):
        e["episode"] = ep
    cols = ["event_id", "point_id", "lat", "lon", "country", "basin", "episode", "upstream_km2", "threshold_m3s",
            "onset", "peak_date", "end", "peak_m3s", "n_above"]
    _write_csv(OUT / "events_all.csv", allev, cols)
    main = cap_sample(allev, C.EVENT_CAP, C.SEED)
    _write_csv(OUT / "events_main.csv", main, cols)
    # section 3: RQ3 main sample = monsoon months (June-October) of 2020-2024, from the forecast archive on
    pool = [e for e in main if C.RQ3_MAIN_YEARS[0] <= int(e["peak_date"][:4]) <= C.RQ3_MAIN_YEARS[1]
            and int(e["peak_date"][5:7]) in C.RQ3_MAIN_MONTHS]
    rq3 = events.rq3_sample(pool, [e["episode"] for e in pool], C.RQ3_SAMPLE_N, C.RQ3_START, C.SEED)
    for k, e in enumerate(rq3):
        e["rq3_order"] = k + 1
        e["rq3_leads"] = "1,3,5" if k < C.RQ3_SECONDARY_N else "3"
    _write_csv(OUT / "rq3_sample.csv", rq3, cols + ["rq3_order", "rq3_leads"])
    placebo = placebo_dates(main, series, C.SEED)
    _write_csv(OUT / "placebo_dates.csv", placebo, ["event_id", "point_id", "placebo_date"])
    check = events.rq3_sample(main, [e["episode"] for e in main], 100, C.PERIOD[0], C.SEED + 1)
    _write_csv(OUT / "blind_check_100.csv", check, ["event_id", "point_id", "lat", "lon", "country", "peak_date"])
    summary = {"points": len(pts), "tiles": len(tiles), "tiles_complete": sorted(done), "points_with_series": len(series), "events_found": len(allev),
               "excluded": counts, "main": len(main), "rq3": len(rq3), "placebo_dates": len(placebo),
               "episodes_main": len({e["episode"] for e in main}),
               "by_year": _count(main, lambda e: e["peak_date"][:4]),
               "by_country": _count(main, lambda e: e["country"])}
    (OUT / "events_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))


def placebo_dates(evs, series, seed, n=2, half=15):
    """Section 9: per event, n non-flood dates at the same point, same day of year +/- half days,
    another study year, discharge below the 2-year threshold for 7 days either side; seeded."""
    import random
    from .thresholds import rp_threshold
    rng = random.Random(seed)
    out = []
    for e in sorted(evs, key=lambda e: e["event_id"]):
        days, qs = series[e["point_id"]]
        thr2 = rp_threshold(e["lat"], e["lon"], 2)
        if thr2 is None:
            continue
        q = dict(zip(days, qs))
        pk = date.fromisoformat(e["peak_date"])
        cands = []
        for y in range(int(C.PERIOD[0][:4]), int(C.PERIOD[1][:4]) + 1):
            if y == pk.year:
                continue
            try:
                c0 = pk.replace(year=y)
            except ValueError:
                c0 = pk.replace(year=y, day=28)
            for k in range(-half, half + 1):
                d = c0 + timedelta(days=k)
                win = [q.get((d + timedelta(days=j)).isoformat()) for j in range(-7, 8)]
                if all(v is not None and v < thr2 for v in win):
                    cands.append(d.isoformat())
        rng.shuffle(cands)
        picked = []
        for d in cands:                       # different years for the two dates
            if all(d[:4] != p[:4] for p in picked):
                picked.append(d)
            if len(picked) == n:
                break
        out += [{"event_id": e["event_id"], "point_id": e["point_id"], "placebo_date": d} for d in sorted(picked)]
    return out


def _pilot_refs():
    """Pilot events for exclusion 4: the GloFAS peak found by the pilot when there is one, else
    every day of the pilot's search window (conservative)."""
    data = json.loads((ROOT / "pilot" / "pilot_events.json").read_text(encoding="utf-8"))["events"]
    refs = []
    for ev in data:
        g = ROOT / "pilot" / "out" / ev["id"] / "glofas.json"
        peak = None
        if g.exists():
            e = json.loads(g.read_text(encoding="utf-8")).get("event")
            peak = e and e.get("peak_date")
        if peak:
            refs.append({"lat": ev["lat"], "lon": ev["lon"], "peak_date": str(peak)[:10]})
        else:
            a, b = (date.fromisoformat(x) for x in ev["search_window"])
            refs += [{"lat": ev["lat"], "lon": ev["lon"], "peak_date": (a + timedelta(days=k)).isoformat()}
                     for k in range((b - a).days + 1)]
    return refs


# ------------------------------------------------------------------ io

def _count(rows, key):
    c = {}
    for r in rows:
        c[key(r)] = c.get(key(r), 0) + 1
    return dict(sorted(c.items()))


def _write_csv(path, rows, cols):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def _read_points():
    with open(OUT / "points.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["lat"], r["lon"], r["upstream_km2"] = float(r["lat"]), float(r["lon"]), float(r["upstream_km2"])
        r["basin"] = int(r["basin"])
    return rows


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", nargs="?", choices=["points", "download", "events"])
    ap.add_argument("--keep-raw", action="store_true", help="keep the downloaded tile NetCDF files")
    a = ap.parse_args()
    if a.step in (None, "points"):
        step_points()
    if a.step in (None, "download"):
        step_download(a.keep_raw)
    if a.step in (None, "events"):
        step_events()
