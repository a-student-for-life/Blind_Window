"""Checking sheet for the human checks (ANALYSIS_PLAN.md section 10, pilot/MANUAL_CHECK_10.md).

    python -m study.checkpage            # pilot events -> pilot/CHECK_SHEET.md
    python -m study.checkpage --main     # main events -> results/CHECK_SHEET_main.md

For each event: the floodplain point on a satellite map (question 2), the GloFAS peak (question 1)
and every acquisition from the peak to 30 days later with the pipeline's usable / not usable call
(questions 3 and 4). Open the point in the Copernicus Browser (browser.dataspace.copernicus.eu) on
the listed date to look at the image itself.
"""
import argparse
from pathlib import Path

from . import pilot

ROOT = Path(__file__).resolve().parent.parent


def sheet(evs, title):
    out = [f"# {title}", "",
           "Answer in pilot/MANUAL_CHECK_10.md (or the main check file) BEFORE reading the pipeline's call.", ""]
    for ev in evs:
        g, fp, ob = (pilot.load(ev["id"], s) for s in ("glofas", "floodplain", "observed"))
        if not (g and g.get("event") and fp and ob and "acquisitions" in ob):
            continue
        e = g["event"]
        lat, lon = round(fp["lat"], 5), round(fp["lon"], 5)
        out += [f"## {ev['id']} {ev.get('name', '')}", "",
                f"- GloFAS peak day: **{str(e['peak_date'])[:10]}** (above the 5-year flow {str(e['onset'])[:10]} to {str(e['end'])[:10]})",
                f"- Floodplain point: {lat}, {lon} — [satellite map](https://www.google.com/maps/@{lat},{lon},2000m/data=!3m1!1e3)",
                f"- Copernicus Browser: open https://browser.dataspace.copernicus.eu, search `{lat}, {lon}`, pick the date below",
                "", "| Date and time (UTC) | Satellite | Pipeline's call (hide this column first) |", "|---|---|---|"]
        t0 = pilot._dt(e["t0"])
        for a in ob["acquisitions"]:
            t = pilot._dt(a["time"])
            if t >= t0 and (t - t0).days <= 30:
                out.append(f"| {t:%Y-%m-%d %H:%M} | {a['satellite']} | {'usable' if a['usable'] else 'not usable'} "
                           f"({100 * a['valid_share']:.0f}% of area valid and clear) |")
        out.append("")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", action="store_true")
    if ap.parse_args().main:
        from . import main as M
        evs, target = M.main_events(), ROOT / "results" / "CHECK_SHEET_main.md"
        target.parent.mkdir(exist_ok=True)
    else:
        evs, target = pilot.pilots(), ROOT / "pilot" / "CHECK_SHEET.md"
    target.write_text(sheet(evs, "Checking sheet"), encoding="utf-8")
    print(f"written {target}")
