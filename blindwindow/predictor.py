"""The Blind Window predictor. Pure functions, no network: easy to test.

Conventions
- A daily discharge value for date D is the mean over D 00:00 to D+1 00:00 UTC.
  The "peak instant" is the END of the peak day (D+1 00:00 UTC). This matches
  EWDS valid_time labels and the lags in the smoke-test report.
- Naive rule: first planned or projected pass after the peak instant.
- Cloud-aware rule: first pass that is SAR, or optical with forecast cloud
  below the threshold. Optical passes with no cloud forecast are "unknown"
  and are not counted as usable.
"""
from datetime import datetime, timedelta, timezone

from .config import AOI_HALF_DEG, CLOUD_USABLE_BELOW


def peak_instant(peak_date):
    d = datetime.fromisoformat(peak_date[:10]).replace(tzinfo=timezone.utc)
    return d + timedelta(days=1)


def classify(p, cloud_pct, threshold=CLOUD_USABLE_BELOW):
    if p["kind"] == "sar":
        return "usable"
    if cloud_pct is None:
        return "unknown"
    return "usable" if cloud_pct < threshold else "cloudy"


def predict(peak_date, passes, cloud_lookup, threshold=CLOUD_USABLE_BELOW):
    """passes: list of dicts with time (datetime), satellite, kind, source.
    cloud_lookup: callable(datetime) -> cloud % or None."""
    t0 = peak_instant(peak_date)
    after = sorted((p for p in passes if p["time"] >= t0), key=lambda p: p["time"])
    rows = []
    for p in after:
        c = cloud_lookup(p["time"]) if p["kind"] == "optical" else None
        rows.append({**p, "cloud_pct": c, "status": classify(p, c, threshold),
                     "lag_h": round((p["time"] - t0).total_seconds() / 3600, 1)})
    naive = rows[0] if rows else None
    aware = next((r for r in rows if r["status"] == "usable"), None)
    unknown_before = [r for r in rows if r["status"] == "unknown" and (aware is None or r["time"] < aware["time"])]
    return {
        "peak_instant": t0,
        "passes_after_peak": rows,
        "naive": naive,
        "cloud_aware": aware,
        "blind_window_h": aware["lag_h"] if aware else None,
        "beyond_horizon": aware is None,
        "unresolved_optical_before": len(unknown_before),
    }


def member_windows(member_peaks, passes, cloud_lookup, threshold=CLOUD_USABLE_BELOW):
    """Blind window for each ensemble member's peak date: a spread, not a probability."""
    out = []
    for m in member_peaks:
        r = predict(m["peak_date"], passes, cloud_lookup, threshold)
        out.append({"member": m["member"], "peak_date": m["peak_date"], "blind_window_h": r["blind_window_h"]})
    return out


def spread(values):
    vals = sorted(v for v in values if v is not None)
    if not vals:
        return None
    pick = lambda q: vals[min(len(vals) - 1, int(q * (len(vals) - 1) + 0.5))]
    return {"n": len(vals), "min": vals[0], "p25": pick(0.25), "median": pick(0.5),
            "p75": pick(0.75), "max": vals[-1]}


def draft_brief(point, cell, result, issued_at):
    """A draft acquisition brief for a planner to review. Never submitted.
    The window ends at the PREDICTED first usable pass (known at issue time),
    never at an observed one."""
    t0 = result["peak_instant"]
    end = result["cloud_aware"]["time"] if result["cloud_aware"] else None
    bw = result["blind_window_h"]
    priority = "urgent" if (bw is None or bw > 72) else "normal"
    lat, lon = cell
    return {
        "status": "DRAFT - not submitted to any agency",
        "issued_at": issued_at.isoformat(),
        "purpose": "Flood monitoring",
        "area_name": point["name"],
        "aoi_bbox": [round(lon - AOI_HALF_DEG, 3), round(lat - AOI_HALF_DEG, 3),
                     round(lon + AOI_HALF_DEG, 3), round(lat + AOI_HALF_DEG, 3)],
        "window_utc": [(t0 - timedelta(days=1)).isoformat(), end.isoformat() if end else "beyond plan horizon"],
        "priority": priority,
        "reason": (f"Predicted gap of {bw:.0f} h between forecast peak and next usable public pass."
                   if bw is not None else "No usable public pass found within the plan horizon."),
    }
