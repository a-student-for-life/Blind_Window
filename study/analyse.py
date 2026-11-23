"""Results for the paper (ANALYSIS_PLAN.md sections 5-8) from the main run's saved outputs.

    python -m study.analyse            # writes results/RESULTS.md, results/*.csv, results/fig_*.png
    python -m study.analyse --pilot    # same, on the pilot events (pilot/out), for a dry run

Reads only files on disk (no downloads), so it can be run again at any time, e.g. after a few
more events finished.
"""
import argparse
import csv
import json
from datetime import timedelta
from pathlib import Path

import numpy as np

from . import config as C, events, pilot, scoring

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
SOUTH_ASIA = {"IND", "PAK", "BGD", "NPL", "BTN", "LKA"}
BASELINES = ["next_any_pass", "next_s1_pass", "climatology"]
LABEL = {"blind_window": "Blind-window forecast", "next_any_pass": "Next pass, any satellite",
         "next_s1_pass": "Next Sentinel-1 pass", "climatology": "Site climatology"}


def collect(evs):
    rows = []
    for ev in evs:
        ob = pilot.load(ev["id"], "observed")
        if not ob or "bw_any_h" not in ob:
            continue
        g = pilot.load(ev["id"], "glofas")
        e = g["event"]
        r = {"event_id": ev["id"], "country": ev.get("country", ""), "episode": ev.get("episode", ev["id"]),
             "year": str(e["peak_date"])[:4], "peak_date": str(e["peak_date"])[:10], "t0": e["t0"],
             "duration_h": (pilot._dt(e["end"]) - pilot._dt(e["onset"])).total_seconds() / 3600}
        for k in ("bw_any_h", "bw_s1_h", "bw_s2_h", "censored_any", "censored_s1", "censored_s2",
                  "missed", "seen_during_flood", "seen_near_peak", "first_usable_mission"):
            r[k] = ob.get(k)
        r["region"] = "South Asia" if r["country"] in SOUTH_ASIA else "Southeast Asia"
        q = pilot.rq2(ev)
        t0 = pilot._dt(e["t0"])
        gap = any(events.in_plan_gap(t0 + timedelta(days=d), s) for s in C.PLAN_GAPS for d in range(*C.RQ2_WINDOW))
        if q and not gap:
            for m in ("S1", "S2"):
                for k in ("n_actual", "n_planned", "n_matched"):
                    r[f"{m}_{k}"] = q[m][k]
                r[f"{m}_usable_matched"] = round((q[m]["usable_precision"] or 0) * q[m]["n_planned"])
        pl = pilot.load(ev["id"], "placebo")
        if pl and pl.get("dates"):
            r["placebo_bw_any_h"] = float(np.mean([x["bw_any_h"] for x in pl["dates"]]))
        fc = pilot.load(ev["id"], "forecast")
        if fc and "leads" in fc:
            for L, v in fc["leads"].items():
                for k, err in v["abs_err_h"].items():
                    r[f"err_L{L}_{k}"] = err
                r[f"peak_err_L{L}_d"] = None if not v["pred_peak_date"] else \
                    (np.datetime64(v["pred_peak_date"]) - np.datetime64(r["peak_date"])).astype(int)
        rows.append(r)
    return rows


def _boot_ci(values, episodes, stat, n=C.N_BOOT):
    v = np.asarray(values, float)
    if len(v) == 0:
        return (None, None)
    b = [stat(v[ix]) for ix in scoring.episode_resamples(episodes, n)]
    return tuple(round(float(x), 1) for x in np.percentile(b, [2.5, 97.5]))


def _km_median(t, c):
    ts, s = scoring.kaplan_meier(t, c)
    return next((x for x, y in zip(ts, s) if y <= 0.5), None)     # None = more than half censored


def rq1(rows, out):
    lines = ["## RQ1. Observed blind window after the peak", "",
             "| Group | Events | Median BW any (h) [95% CI] | Median BW S1 (h) | Median BW S2 (h) | Missed (%) [95% CI] | Seen while flooded (%) |",
             "|---|---|---|---|---|---|---|"]
    groups = [("All", rows)] + [(g, [r for r in rows if r["region"] == g]) for g in ("South Asia", "Southeast Asia")] + \
             [(y, [r for r in rows if r["year"] == y]) for y in sorted({r["year"] for r in rows})]
    for name, rs in groups:
        if not rs:
            continue
        ep = [r["episode"] for r in rs]
        t = [r["bw_any_h"] for r in rs]
        c = [r["censored_any"] for r in rs]
        med = _km_median(t, c)
        ci = _boot_ci(np.arange(len(rs)), ep, lambda ix: _km_median(np.array(t)[ix.astype(int)], np.array(c)[ix.astype(int)]) or C.CENSOR_H) \
            if name == "All" else (None, None)
        m1 = _km_median([r["bw_s1_h"] for r in rs], [r["censored_s1"] for r in rs])
        m2 = _km_median([r["bw_s2_h"] for r in rs], [r["censored_s2"] for r in rs])
        miss = [float(bool(r["missed"])) for r in rs]
        mci = _boot_ci(miss, ep, lambda v: 100 * v.mean())
        seen = 100 * np.mean([bool(r["seen_during_flood"]) for r in rs])
        f = lambda x: "> 720" if x is None else f"{x:.0f}"
        lines.append(f"| {name} | {len(rs)} | {f(med)}" + (f" [{ci[0]:.0f}, {ci[1]:.0f}]" if ci[0] is not None else "") +
                     f" | {f(m1)} | {f(m2)} | {100 * np.mean(miss):.0f} [{mci[0]:.0f}, {mci[1]:.0f}] | {seen:.0f} |")
    first = {}
    for r in rows:
        first[r["first_usable_mission"] or "none in 30 days"] = first.get(r["first_usable_mission"] or "none in 30 days", 0) + 1
    pr = [r for r in rows if r.get("placebo_bw_any_h") is not None]
    if pr:
        diff = [r["bw_any_h"] - r["placebo_bw_any_h"] for r in pr]
        ci = _boot_ci(diff, [r["episode"] for r in pr], lambda v: v.mean())
        lines += ["", f"Placebo contrast (section 9): flood minus non-flood dates at the same points, mean "
                      f"{np.mean(diff):.0f} h [95% CI {ci[0]:.0f}, {ci[1]:.0f}], {len(pr)} events "
                      f"(blind windows capped at {C.CENSOR_H} h)."]
    lines += ["", "First usable image by mission: " + ", ".join(f"{k} {v}" for k, v in sorted(first.items())), ""]
    _km_figure(rows, out / "fig_rq1_survival.png")
    lines += ["![Share of floods not yet seen](fig_rq1_survival.png)", ""]
    return lines


def _km_figure(rows, path):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    for key, lab in (("any", "Any satellite"), ("s1", "Sentinel-1"), ("s2", "Sentinel-2")):
        ts, s = scoring.kaplan_meier([r[f"bw_{key}_h"] for r in rows], [r[f"censored_{key}"] for r in rows])
        ax.step([0] + ts, [1.0] + s, where="post", label=lab)
    ax.set_xlabel("Hours after the flood peak")
    ax.set_ylabel("Share of floods not yet seen")
    ax.set_xlim(0, C.CENSOR_H)
    ax.set_ylim(0, 1)
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def rq2(rows):
    lines = ["## RQ2. Do the published plans match what was acquired?", "",
             "| Mission | Year | Events | Real acquisitions | Planned | Recall (real that were planned) | Precision (planned that were acquired) | Usable precision |",
             "|---|---|---|---|---|---|---|---|"]
    for m in ("S1", "S2"):
        rs_all = [r for r in rows if f"{m}_n_actual" in r]
        for y in ["All"] + sorted({r["year"] for r in rs_all}):
            rs = rs_all if y == "All" else [r for r in rs_all if r["year"] == y]
            a = sum(r[f"{m}_n_actual"] for r in rs)
            p = sum(r[f"{m}_n_planned"] for r in rs)
            k = sum(r[f"{m}_n_matched"] for r in rs)
            u = sum(r[f"{m}_usable_matched"] for r in rs)
            f = lambda x, n: f"{x / n:.2f}" if n else "-"
            lines.append(f"| {m} | {y} | {len(rs)} | {a} | {p} | {f(k, a)} | {f(k, p)} | {f(u, p)} |")
    return lines + ["", "Events in a known plan-archive gap are left out of this table (exclusion 3).", ""]


def rq3(rows, out):
    lines = ["## RQ3. Can the blind window be forecast?", ""]
    for L in [str(C.LEAD_DAYS_MAIN)] + [str(x) for x in C.LEAD_DAYS_SECONDARY]:
        rs = [r for r in rows if r.get(f"err_L{L}_blind_window") is not None]
        if not rs:
            continue
        ew = [r[f"err_L{L}_blind_window"] for r in rs]
        ep = [r["episode"] for r in rs]
        main = L == str(C.LEAD_DAYS_MAIN)
        lines += [f"### Lead {L} days ({'main test' if main else 'secondary'}), {len(rs)} events, "
                  f"{len(set(ep))} episodes", "",
                  f"MAE of the blind-window forecast: {np.mean(ew):.1f} h; hit rate within ±{C.HIT_TOL_H} h: "
                  f"{100 * np.mean(np.array(ew) <= C.HIT_TOL_H):.0f}%.", "",
                  "| Baseline | MAE (h) | ΔMAE (h) [95% CI] | p | p (Holm) | Hit rate ±12 h | Reading |", "|---|---|---|---|---|---|---|"]
        res = {}
        for b in BASELINES:
            pairs = [(r[f"err_L{L}_{b}"], r[f"err_L{L}_blind_window"], r["episode"]) for r in rs if r.get(f"err_L{L}_{b}") is not None]
            if len(pairs) < 3:
                continue
            res[b] = (scoring.delta_mae([p[0] for p in pairs], [p[1] for p in pairs], [p[2] for p in pairs]), pairs)
        adj = scoring.holm([v[0]["p"] for v in res.values()]) if res else []
        for (b, (d, pairs)), ph in zip(res.items(), adj):
            eb = np.array([p[0] for p in pairs])
            reading = scoring.verdict(d, ph) if main else "secondary"
            lines.append(f"| {LABEL[b]} | {eb.mean():.1f} | {d['delta_mae_h']:.1f} [{d['ci95'][0]:.1f}, {d['ci95'][1]:.1f}] | "
                         f"{d['p']:.3f} | {ph:.3f} | {100 * np.mean(eb <= C.HIT_TOL_H):.0f}% | {reading} |")
        pe = [r.get(f"peak_err_L{L}_d") for r in rs if r.get(f"peak_err_L{L}_d") is not None]
        if pe:
            lines += ["", f"GloFAS peak-day error (predicted minus observed, days): median {np.median(pe):.0f}, "
                          f"exact in {100 * np.mean(np.array(pe) == 0):.0f}%, within ±1 day in {100 * np.mean(np.abs(pe) <= 1):.0f}%."]
        lines.append("")
    return lines


def write_csv(rows, path):
    cols = sorted({k for r in rows for k in r})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)


def run(use_pilot=False):
    if use_pilot:
        pilot.OUT = ROOT / "pilot" / "out"
        evs = [{**e, "episode": e["id"]} for e in pilot.pilots()]
        out = RES / "pilot_dry_run"
    else:
        from . import main as M
        evs = []
        for e in M.main_events():
            evs.append({**e, "country": e["row"]["country"], "episode": e["row"]["episode"]})
        out = RES
    out.mkdir(parents=True, exist_ok=True)
    rows = collect(evs)
    write_csv(rows, out / "events_results.csv")
    lines = [f"# Results ({'pilot dry run' if use_pilot else 'main set'})", "",
             f"Generated by `python -m study.analyse{' --pilot' if use_pilot else ''}` from {len(rows)} events with "
             f"an observed blind window. Plan: ANALYSIS_PLAN.md v1 with DEVIATIONS.md.", ""]
    if rows:
        lines += rq1(rows, out) + rq2(rows) + rq3(rows, out)
    (out / "RESULTS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pilot", action="store_true")
    run(ap.parse_args().pilot)
