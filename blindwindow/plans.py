"""ESA Sentinel-1/2 acquisition plans: discover KML files, parse footprints,
find passes over a point, and project beyond the plan horizon."""
import io
import re
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from . import http
from .config import CLUSTER_HOURS, REPEAT_DAYS

PAGES = {
    "S1": "https://sentinels.copernicus.eu/copernicus/sentinel-1/acquisition-plans",
    "S2": "https://sentinels.copernicus.eu/copernicus/sentinel-2/acquisition-plans",
}
BASE = "https://sentinels.copernicus.eu"
NAME_RE = re.compile(r"(s[12][a-d])_mp_(?:user|acq_?_?kml)_?_?(\d{8}t\d{6})_(\d{8}t\d{6})", re.I)
ISO_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?")


def _dt(s):
    return datetime.strptime(s.upper(), "%Y%m%dT%H%M%S").replace(tzinfo=timezone.utc)


def parse_iso(s):
    m = ISO_RE.search(s or "")
    if not m:
        return None
    txt = m.group(0)
    if "." in txt:
        head, frac = txt.split(".")
        txt = f"{head}.{frac[:6].ljust(6, '0')}"
    return datetime.fromisoformat(txt).replace(tzinfo=timezone.utc)


def discover(now, horizon_days=30):
    """Return {satellite: link} choosing, per satellite, the newest plan file
    that has started by `now` and still covers some of the horizon."""
    found = {}
    for mission, page in PAGES.items():
        html = http.get(page, cache=False)
        for href in set(re.findall(r'href="([^"]+)"', html)):
            m = NAME_RE.search(href)
            if not m:
                continue
            sat, start, end = m.group(1).upper(), _dt(m.group(2)), _dt(m.group(3))
            if start > now or end < now:
                continue
            link = href if href.startswith("http") else BASE + href
            cur = found.get(sat)
            if cur is None or start > cur["start"]:
                found[sat] = {"satellite": sat, "url": link, "start": start, "end": end}
    return found


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def parse_kml(data, satellite):
    """Parse KML or KMZ bytes into footprints: {satellite, start, end, mode, polygon}."""
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            name = next(n for n in z.namelist() if n.lower().endswith(".kml"))
            data = z.read(name)
    root = ET.fromstring(data)
    out = []
    for pm in root.iter():
        if _local(pm.tag) != "Placemark":
            continue
        coords, begin, end, mode, any_times = None, None, None, None, []
        for el in pm.iter():
            tag, text = _local(el.tag), (el.text or "").strip()
            if tag == "coordinates" and coords is None:
                coords = text
            elif tag == "begin":
                begin = parse_iso(text)
            elif tag == "end":
                end = parse_iso(text)
            elif tag in ("Data", "SimpleData"):
                name = (el.get("name") or "").lower()
                val = text or "".join((c.text or "") for c in el).strip()
                if "mode" in name and not mode:
                    mode = val
                t = parse_iso(val)
                if t:
                    any_times.append((name, t))
        if not coords:
            continue
        if begin is None and any_times:
            starts = [t for n, t in any_times if "start" in n or "begin" in n]
            begin = min(starts) if starts else min(t for _, t in any_times)
            ends = [t for n, t in any_times if "stop" in n or "end" in n]
            end = max(ends) if ends else None
        if begin is None:
            continue
        poly = []
        for tok in coords.split():
            parts = tok.split(",")
            if len(parts) >= 2:
                poly.append((float(parts[0]), float(parts[1])))
        if len(poly) >= 3:
            out.append({"satellite": satellite, "start": begin, "end": end or begin,
                        "mode": mode, "polygon": poly})
    return out


def contains(poly, lon, lat):
    inside, j = False, len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def passes_over(footprints, lat, lon):
    """Footprints containing the point, clustered per satellite into passes."""
    hits = sorted((f for f in footprints if contains(f["polygon"], lon, lat)),
                  key=lambda f: (f["satellite"], f["start"]))
    passes = []
    for f in hits:
        last = passes[-1] if passes else None
        if last and last["satellite"] == f["satellite"] and \
                f["start"] - last["time"] <= timedelta(hours=CLUSTER_HOURS):
            continue
        passes.append({"satellite": f["satellite"], "time": f["start"], "mode": f["mode"],
                       "kind": "sar" if f["satellite"].startswith("S1") else "optical",
                       "source": "planned"})
    return sorted(passes, key=lambda p: p["time"])


def project(passes, plan_end_by_sat, until):
    """Extend each satellite's planned passes past its plan file end using its
    repeat cycle. Projected passes are labelled and never replace planned ones."""
    out = list(passes)
    for sat, plan_end in plan_end_by_sat.items():
        mine = [p for p in passes if p["satellite"] == sat]
        if not mine:
            continue
        step = timedelta(days=REPEAT_DAYS[sat[:2]])
        # one projection chain per distinct orbit slot seen in the plan window
        for seed in mine:
            t = seed["time"] + step
            while t <= until:
                if t > plan_end:
                    out.append({**seed, "time": t, "source": "projected"})
                t += step
    # drop projected duplicates landing within the cluster window of another pass
    out.sort(key=lambda p: (p["time"], p["source"] != "planned"))
    dedup = []
    for p in out:
        if any(q["satellite"] == p["satellite"] and abs(q["time"] - p["time"]) <= timedelta(hours=CLUSTER_HOURS)
               for q in dedup):
            continue
        dedup.append(p)
    return dedup


def load_footprints(now, horizon_days=30):
    files = discover(now, horizon_days)
    footprints, meta = [], []
    for sat, info in sorted(files.items()):
        try:
            data = http.get(info["url"], binary=True)
            fps = parse_kml(data, sat)
            footprints += fps
            meta.append({**info, "start": info["start"].isoformat(), "end": info["end"].isoformat(),
                         "n_footprints": len(fps)})
        except Exception as e:
            meta.append({**info, "start": info["start"].isoformat(), "end": info["end"].isoformat(),
                         "error": repr(e)})
    return footprints, meta, {s: i["end"] for s, i in files.items()}
