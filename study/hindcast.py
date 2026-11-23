"""Forecast replay "as of" the issue time (ANALYSIS_PLAN.md section 7).

Everything passed in must have been available at tau: the GloFAS forecast issued at tau, the plans
issued >= 24 h before each pass, and the cloud expectation for each S2 pass. Since deviation 2
the cloud expectation is the site's usual cloudiness (cloud_climatology_factory), not TIGGE.
"""
import statistics
from datetime import datetime, timedelta, timezone

from blindwindow import plans as bw_plans
from blindwindow import predictor

from . import config as C


def issue_time(obs_peak_date, lead_days=C.LEAD_DAYS_MAIN):
    d = obs_peak_date - timedelta(days=lead_days)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


def predicted_peak(fc_dates, member_series):
    """Day of maximum of the ensemble median. member_series: list of per-member lists aligned with
    fc_dates (None = missing)."""
    med = []
    for k in range(len(fc_dates)):
        vals = [m[k] for m in member_series if m[k] is not None]
        med.append(statistics.median(vals) if vals else None)
    pts = [(v, -k) for k, v in enumerate(med) if v is not None]
    if not pts:
        return None
    v, negk = max(pts)                     # ties: earliest day
    return str(fc_dates[-negk])[:10]


def cloud_lookup_factory(tau, steps, max_h=C.CLOUD_FORECAST_MAX_H):
    """steps: sorted list of (valid_time, tcc_percent) from the TIGGE ensemble mean issued at tau.
    Linear interpolation; None beyond max_h or outside the series."""
    def look(t):
        if (t - tau).total_seconds() > max_h * 3600 or not steps:
            return None
        for (ta, ca), (tb, cb) in zip(steps, steps[1:]):
            if ta <= t <= tb:
                w = (t - ta).total_seconds() / max((tb - ta).total_seconds(), 1)
                return ca + w * (cb - ca)
        return None
    return look


def cloud_climatology_factory(past_s2, event_year, half_days=C.CLOUD_CLIM_HALF_DAYS,
                              min_passes=C.CLOUD_CLIM_MIN_PASSES):
    """Deviation 2: usual cloudiness at the point. past_s2: list of (datetime, cloud_pct) for S2
    passes over the point in other years, cloud_pct = 100 x (1 - clear share of the area).
    look(t) = mean cloud_pct of the passes in other years within +/- half_days of t's day of year;
    None (unknown, not usable) when fewer than min_passes."""
    rows = [(t.timetuple().tm_yday, c) for t, c in past_s2 if t.year != event_year]

    def look(t):
        doy = t.timetuple().tm_yday
        vals = [c for d, c in rows if min(abs(d - doy), 365 - abs(d - doy)) <= half_days]
        return sum(vals) / len(vals) if len(vals) >= min_passes else None
    return look


def forecast(tau, pred_peak_date, planned_passes, plan_end_by_sat, cloud_steps=None, cloud_look=None):
    """cloud_look (a function of time) is used when given; otherwise TIGGE steps (cloud_steps)."""
    passes = bw_plans.project(planned_passes, plan_end_by_sat, tau + timedelta(days=C.SEARCH_DAYS + 30))
    look = cloud_look or cloud_lookup_factory(tau, cloud_steps or [])
    r = predictor.predict(pred_peak_date, passes, look, C.S2_CLOUD_FORECAST_USABLE_BELOW)
    return {"tau": tau, "pred_peak_date": pred_peak_date,
            "t_hat": r["cloud_aware"]["time"] if r["cloud_aware"] else None,
            "naive_time": r["naive"]["time"] if r["naive"] else None,
            "result": r}
