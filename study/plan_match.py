"""Plans against acquisitions (ANALYSIS_PLAN.md section 6). Pure functions."""
from datetime import timedelta

from . import config as C


def plan_available(plans, t, lead_h=C.PLAN_LEAD_H):
    """Latest plan per satellite issued at least lead_h before t.
    plans: dicts with satellite, issued (datetime), start, end."""
    cutoff = t - timedelta(hours=lead_h)
    best = {}
    for p in plans:
        if p["issued"] <= cutoff and (p["satellite"] not in best or p["issued"] > best[p["satellite"]]["issued"]):
            best[p["satellite"]] = p
    return best


def match(planned, actual, tol_min=C.MATCH_TOL_MIN):
    """One-to-one greedy matching by time within tol_min minutes, same satellite.
    planned/actual: dicts with satellite, time. Returns (pairs, unplanned_actual, unacquired_planned)."""
    tol = timedelta(minutes=tol_min)
    free = sorted(range(len(actual)), key=lambda i: actual[i]["time"])
    pairs, used = [], set()
    for p in sorted(planned, key=lambda p: p["time"]):
        best = None
        for i in free:
            a = actual[i]
            if i in used or a["satellite"] != p["satellite"]:
                continue
            d = abs(a["time"] - p["time"])
            if d <= tol and (best is None or d < best[0]):
                best = (d, i)
        if best:
            used.add(best[1])
            pairs.append((p, actual[best[1]]))
    unplanned = [actual[i] for i in range(len(actual)) if i not in used]
    matched_p = {id(p) for p, _ in pairs}
    unacquired = [p for p in planned if id(p) not in matched_p]
    return pairs, unplanned, unacquired


def completeness(planned, actual, tol_min=C.MATCH_TOL_MIN):
    pairs, unplanned, unacquired = match(planned, actual, tol_min)
    n_a, n_p = len(actual), len(planned)
    usable_pairs = sum(1 for _, a in pairs if a.get("usable"))
    return {"n_actual": n_a, "n_planned": n_p, "n_matched": len(pairs),
            "recall": len(pairs) / n_a if n_a else None,
            "precision": len(pairs) / n_p if n_p else None,
            "usable_precision": usable_pairs / n_p if n_p else None,
            "unplanned": unplanned, "unacquired": unacquired}
