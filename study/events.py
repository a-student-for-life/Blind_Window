"""Event definition (ANALYSIS_PLAN.md section 3). Pure functions, no network."""
import math
from datetime import date, datetime, timedelta, timezone

from . import config as C


def _d(x):
    return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


def detect_events(dates, discharge, threshold, merge_days=C.MERGE_DAYS):
    """Exceedance runs above `threshold`, merged when separated by <= merge_days days.

    dates: consecutive daily dates (ISO strings or date). discharge: same length, None = missing
    (missing days are treated as not above). Returns a list of dicts with onset, end, peak_date,
    peak_m3s, n_above (dates are datetime.date; onset/end are the first/last above days)."""
    days = [_d(d) for d in dates]
    above = [q is not None and q > threshold for q in discharge]
    runs, i = [], 0
    while i < len(days):
        if above[i]:
            j = i
            while j + 1 < len(days) and above[j + 1]:
                j += 1
            runs.append([i, j])
            i = j + 1
        else:
            i += 1
    merged = []
    for r in runs:
        if merged and (days[r[0]] - days[merged[-1][1]]).days - 1 <= merge_days:
            merged[-1][1] = r[1]
        else:
            merged.append(list(r))
    out = []
    for a, b in merged:
        seg = [(discharge[k], k) for k in range(a, b + 1) if discharge[k] is not None]
        qmax = max(q for q, _ in seg)
        k_peak = min(k for q, k in seg if q == qmax)           # ties: earliest
        out.append({"onset": days[a], "end": days[b], "peak_date": days[k_peak], "peak_m3s": qmax,
                    "n_above": sum(above[a:b + 1])})
    return out


def instants(ev):
    """t0 = end of peak day; onset = start of first above day; end = end of last above day (UTC)."""
    utc = timezone.utc
    start = lambda d: datetime(d.year, d.month, d.day, tzinfo=utc)
    return {"t0": start(ev["peak_date"]) + timedelta(days=1),
            "onset": start(ev["onset"]),
            "end": start(ev["end"]) + timedelta(days=1)}


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def thin_points(cells, min_upstream=C.MIN_UPSTREAM_KM2, km=C.THIN_KM):
    """cells: dicts with lat, lon, upstream_km2, outlet (id of the river's outlet), lake (bool).
    Greedy, largest upstream area first; drop a cell within `km` of a kept cell with the same outlet."""
    cand = sorted((c for c in cells if c["upstream_km2"] >= min_upstream and not c.get("lake")),
                  key=lambda c: (-c["upstream_km2"], c["lat"], c["lon"]))
    kept = []
    for c in cand:
        if any(k["outlet"] == c["outlet"] and haversine_km(k["lat"], k["lon"], c["lat"], c["lon"]) < km
               for k in kept):
            continue
        kept.append(c)
    return kept


def episodes(events, days=C.EPISODE_DAYS):
    """Assign episode ids: same basin (event['basin']) and peaks linked within `days` (single linkage).
    Returns a list of episode ids aligned with `events`."""
    order = sorted(range(len(events)), key=lambda i: (events[i]["basin"], _d(events[i]["peak_date"])))
    ids, cur, last_basin, last_peak = [None] * len(events), -1, None, None
    for i in order:
        b, p = events[i]["basin"], _d(events[i]["peak_date"])
        if b != last_basin or (p - last_peak).days > days:
            cur += 1
        ids[i], last_basin, last_peak = cur, b, p
    return ids


def near_pilot(ev, pilots, km=C.PILOT_EXCLUSION_KM, days=C.PILOT_EXCLUSION_DAYS):
    """Exclusion 4: within km and days of any pilot event."""
    return any(haversine_km(ev["lat"], ev["lon"], p["lat"], p["lon"]) <= km and
               abs((_d(ev["peak_date"]) - _d(p["peak_date"])).days) <= days for p in pilots)


def in_plan_gap(t0, satellite, gaps=C.PLAN_GAPS):
    d = t0.date() if isinstance(t0, datetime) else _d(t0)
    return any(_d(a) <= d <= _d(b) for a, b in gaps.get(satellite, []))


def rq3_sample(events, episode_ids, n, start, seed):
    """Deviation 3: seeded random subset for the forecast test. events: dicts with peak_date
    (ISO string or date) and an id; episode_ids aligned with events. Only peaks on or after start;
    at most one event per episode; stratified by year (proportional, largest remainder).
    Returns the chosen events in a seeded random order (the first ones also run at leads 1, 5)."""
    import random
    rng = random.Random(seed)
    order = list(range(len(events)))
    rng.shuffle(order)
    seen, pool = set(), []
    for i in order:
        if str(events[i]["peak_date"])[:10] < start or episode_ids[i] in seen:
            continue
        seen.add(episode_ids[i])
        pool.append(events[i])
    if len(pool) <= n:
        return pool
    by_year = {}
    for e in pool:
        by_year.setdefault(str(e["peak_date"])[:4], []).append(e)
    quota = {y: n * len(v) / len(pool) for y, v in by_year.items()}
    take = {y: int(q) for y, q in quota.items()}
    for y in sorted(quota, key=lambda y: (-(quota[y] - take[y]), y))[: n - sum(take.values())]:
        take[y] += 1
    chosen = {id(e) for y, v in by_year.items() for e in v[: take[y]]}
    return [e for e in pool if id(e) in chosen]
