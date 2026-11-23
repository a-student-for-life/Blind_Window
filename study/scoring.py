"""Scoring (ANALYSIS_PLAN.md sections 5, 7, 8). Episode bootstrap and Holm, adapted from
WAKE stage_b/analyse.py."""
import numpy as np

from . import config as C


def holm(ps):
    """Holm step-down adjusted p-values (same as WAKE stage_b/analyse.holm)."""
    ps = np.asarray(ps, float)
    o = np.argsort(ps)
    adj = np.empty_like(ps)
    run = 0.0
    for k, i in enumerate(o):
        run = max(run, min(1.0, (len(ps) - k) * ps[i]))
        adj[i] = run
    return adj


def episode_resamples(episode_ids, n_boot=C.N_BOOT, seed=C.SEED):
    """Index arrays: each resample draws episodes with replacement and keeps all their rows."""
    ep = np.asarray(episode_ids)
    uniq = np.unique(ep)
    rows = {u: np.flatnonzero(ep == u) for u in uniq}
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        pick = rng.choice(uniq, size=len(uniq), replace=True)
        yield np.concatenate([rows[u] for u in pick])


def abs_err_h(pred, obs, cap=C.CENSOR_H):
    return np.minimum(np.abs((np.asarray(pred, float) - np.asarray(obs, float))), cap)


def delta_mae(err_base, err_bw, episode_ids, n_boot=C.N_BOOT, seed=C.SEED):
    """Paired ΔMAE = MAE_baseline - MAE_BlindWindow with episode-bootstrap 95% CI and a two-sided
    bootstrap p-value (share of resamples on the other side of 0, doubled)."""
    eb, ew = np.asarray(err_base, float), np.asarray(err_bw, float)
    est = eb.mean() - ew.mean()
    boots = np.array([eb[ix].mean() - ew[ix].mean() for ix in episode_resamples(episode_ids, n_boot, seed)])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    p = min(1.0, 2 * min((boots <= 0).mean(), (boots >= 0).mean()))
    return {"delta_mae_h": float(est), "ci95": (float(lo), float(hi)), "p": float(p), "n": int(len(eb))}


def verdict(res, p_holm, gain=C.MIN_USEFUL_GAIN_H, alpha=C.ALPHA):
    """Section 8 reading rules."""
    if p_holm < alpha and res["delta_mae_h"] >= gain:
        return "beats baseline by a useful margin"
    if res["ci95"][1] < gain:
        return "no useful gain"
    return "inconclusive"


def kaplan_meier(times_h, censored):
    """Survival of 'not yet seen': returns sorted event times and S(t) just after each."""
    t = np.asarray(times_h, float)
    c = np.asarray(censored, bool)
    order = np.argsort(t)
    t, c = t[order], c[order]
    n, s, out_t, out_s = len(t), 1.0, [], []
    i = 0
    while i < len(t):
        j = i
        while j < len(t) and t[j] == t[i]:
            j += 1
        d = int((~c[i:j]).sum())
        if d:
            s *= 1 - d / n
            out_t.append(float(t[i]))
            out_s.append(s)
        n -= j - i
        i = j
    return out_t, out_s
