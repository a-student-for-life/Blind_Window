"""River discharge from the Open-Meteo Flood API (GloFAS): snapping and forecasts."""
import json
from pathlib import Path

from . import http
from .config import (FORECAST_DAYS, FORECAST_MODEL, SNAP_GRID_HALF, SNAP_GRID_STEP,
                     SNAP_MODELS, SNAP_WINDOW)

API = "https://flood-api.open-meteo.com/v1/flood"
SNAP_FILE = Path(__file__).resolve().parent.parent / "data" / "snaps.json"


def _as_list(resp):
    return resp if isinstance(resp, list) else [resp]


def _series_max(daily):
    vals = [(v, d) for d, v in zip(daily.get("time", []), daily.get("river_discharge", [])) if v is not None]
    if not vals:
        return None, None, 0
    v, d = max(vals)
    return v, d, len(vals)


def grid(lat, lon, half=SNAP_GRID_HALF, step=SNAP_GRID_STEP):
    return [(round(lat + i * step, 4), round(lon + j * step, 4))
            for i in range(-half, half + 1) for j in range(-half, half + 1)]


def choose_cell(candidates, min_peak):
    """Pure function: pick the main-stem cell from scanned candidates.

    candidates: list of dicts with lat, lon, max_m3s (None if no data).
    Returns (best, status). Identical series (same max) are de-duplicated by
    keeping the candidate closest to the seed, which the caller lists first.
    """
    valid = [c for c in candidates if c["max_m3s"] is not None]
    if not valid:
        return None, "no_data"
    best = max(valid, key=lambda c: c["max_m3s"])
    if best["max_m3s"] < min_peak:
        return best, "below_min_peak"
    return best, "ok"


def snap(point, refresh=False):
    """Scan a 7x7 grid around the seed over a past monsoon window and keep the
    cell with the largest discharge. Results are cached in data/snaps.json."""
    snaps = json.loads(SNAP_FILE.read_text()) if SNAP_FILE.exists() else {}
    if point["id"] in snaps and not refresh:
        return snaps[point["id"]]

    cells = grid(point["lat"], point["lon"])
    # closest-to-seed first, so ties resolve toward the seed
    cells.sort(key=lambda c: (c[0] - point["lat"]) ** 2 + (c[1] - point["lon"]) ** 2)
    result = {"seed": [point["lat"], point["lon"]], "window": list(SNAP_WINDOW), "tried": []}
    for model in SNAP_MODELS:
        resp = http.get_json(API, {
            "latitude": ",".join(str(c[0]) for c in cells),
            "longitude": ",".join(str(c[1]) for c in cells),
            "daily": "river_discharge", "models": model,
            "start_date": SNAP_WINDOW[0], "end_date": SNAP_WINDOW[1],
        })
        cands = []
        for (lat, lon), loc in zip(cells, _as_list(resp)):
            mx, date, n = _series_max(loc.get("daily", {}))
            cands.append({"lat": lat, "lon": lon, "max_m3s": mx, "max_date": date, "n_values": n})
        best, status = choose_cell(cands, point["min_peak_m3s"])
        result["tried"].append({"model": model, "status": status,
                                "n_cells_with_data": sum(c["max_m3s"] is not None for c in cands)})
        if best is not None and status == "ok":
            result.update({"status": "ok", "model": model, "lat": best["lat"], "lon": best["lon"],
                           "snap_max_m3s": best["max_m3s"], "snap_max_date": best["max_date"]})
            break
        if best is not None:
            result.update({"status": status, "model": model, "lat": best["lat"], "lon": best["lon"],
                           "snap_max_m3s": best["max_m3s"], "snap_max_date": best["max_date"]})
    else:
        result.setdefault("status", "no_data")

    snaps[point["id"]] = result
    SNAP_FILE.parent.mkdir(parents=True, exist_ok=True)
    SNAP_FILE.write_text(json.dumps(snaps, indent=2))
    return result


def summarize_forecast(daily):
    """Pure function: central peak plus per-member peak dates from a daily block."""
    times = daily.get("time", [])
    central = [(v, t) for t, v in zip(times, daily.get("river_discharge", [])) if v is not None]
    members = []
    for key, vals in daily.items():
        if key.startswith("river_discharge_member"):
            pts = [(v, t) for t, v in zip(times, vals) if v is not None]
            if pts:
                v, t = max(pts)
                members.append({"member": key.rsplit("member", 1)[1], "peak_date": t, "peak_m3s": v})
    out = {"dates": times, "central": daily.get("river_discharge", []), "members": members}
    if central:
        v, t = max(central)
        out.update({"peak_date": t, "peak_m3s": v})
    elif members:  # some responses only carry members
        dates = sorted(m["peak_date"] for m in members)
        out.update({"peak_date": dates[len(dates) // 2], "peak_m3s": None, "peak_from": "member_median"})
    if members:
        dates = sorted(m["peak_date"] for m in members)
        out["member_peak_min"], out["member_peak_max"] = dates[0], dates[-1]
        out["member_peak_median"] = dates[len(dates) // 2]
    return out


def forecast(lat, lon):
    resp = http.get_json(API, {
        "latitude": lat, "longitude": lon, "daily": "river_discharge",
        "models": FORECAST_MODEL, "forecast_days": FORECAST_DAYS, "ensemble": "true",
    }, cache=False)
    return summarize_forecast(_as_list(resp)[0].get("daily", {}))
