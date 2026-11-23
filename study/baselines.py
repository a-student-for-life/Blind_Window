"""Baselines for the forecast test (ANALYSIS_PLAN.md section 7). Pure functions."""
import statistics
from datetime import timedelta

from blindwindow import predictor

from . import config as C


def next_any_pass(pred_peak_date, passes):
    """Baseline 1: first planned or projected pass after the predicted peak, ignoring cloud."""
    r = predictor.predict(pred_peak_date, passes, lambda t: None)
    return r["naive"]["time"] if r["naive"] else None


def next_s1_projection(pred_peak_date, past_s1, tau, repeat_days=12,
                       lookback_days=C.NEXT_S1_LOOKBACK_DAYS):
    """Baseline 2: S1 acquisitions over the point in the lookback before tau, each projected
    forward by the repeat cycle; the first projected time after the predicted peak instant.
    past_s1: dicts with satellite, time (actual acquisitions, ASF records)."""
    t0 = predictor.peak_instant(pred_peak_date)
    step = timedelta(days=repeat_days)
    seeds = [a for a in past_s1 if tau - timedelta(days=lookback_days) <= a["time"] < tau]
    best = None
    for a in seeds:
        t = a["time"]
        while t < t0:
            t += step
        if best is None or t < best:
            best = t
    return best


def climatology(pred_peak_date, site_bw_by_start, event_year, month):
    """Baseline 3: predicted peak instant + median observed blind window (any mission) for start
    dates in the same calendar month in other years. site_bw_by_start: list of (date, bw_h)."""
    vals = [bw for d, bw in site_bw_by_start if d.month == month and d.year != event_year]
    if not vals:
        return None
    return predictor.peak_instant(pred_peak_date) + timedelta(hours=statistics.median(vals))
