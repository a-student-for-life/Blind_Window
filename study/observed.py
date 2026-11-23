"""Observed blind window (ANALYSIS_PLAN.md section 5).

The pure part (blind_window) takes a list of acquisitions already classed usable or not.
The Earth Engine part (ee_acquisitions) is imported lazily and only runs after study.guard allows it.
It has not been run yet: the pilot is its first test.
"""
from datetime import timedelta

from . import config as C


def blind_window(inst, acquisitions, censor_h=C.CENSOR_H):
    """inst: dict with t0, onset, end (datetimes). acquisitions: dicts with time, mission ('S1'|'S2'),
    usable (bool). Returns hours to first usable for S1, S2 and either, plus missed/seen flags."""
    t0, horizon = inst["t0"], inst["t0"] + timedelta(hours=censor_h)
    usable = sorted((a for a in acquisitions if a["usable"]), key=lambda a: a["time"])

    def first_after(mission=None):
        a = next((a for a in usable if a["time"] >= t0 and a["time"] <= horizon
                  and (mission is None or a["mission"] == mission)), None)
        return (round((a["time"] - t0).total_seconds() / 3600, 2), False, a) if a else (censor_h, True, None)

    out = {}
    for key, m in (("any", None), ("s1", "S1"), ("s2", "S2")):
        h, cens, a = first_after(m)
        out[f"bw_{key}_h"], out[f"censored_{key}"] = h, cens
        if key == "any":
            out["first_usable_time"] = a["time"] if a else None
            out["first_usable_mission"] = a["mission"] if a else None
    first = out["first_usable_time"]
    out["missed"] = first is None or first > inst["end"]
    out["seen_during_flood"] = any(inst["onset"] <= a["time"] <= inst["end"] for a in usable)
    out["seen_near_peak"] = any(abs((a["time"] - t0).total_seconds()) <= 24 * 3600 for a in usable)
    return out


# ---------------------------------------------------------------- Earth Engine (lazy, untested)

def ee_acquisitions(lat, lon, start, end, radius_m=C.RADIUS_M, min_valid=C.MIN_VALID_SHARE,
                    cloud_max=C.S2_CLOUD_PROB_MAX):
    """Per-acquisition usability at a point, from Earth Engine. Returns a list of dicts
    {time, mission, satellite, usable, valid_share}. One entry per satellite pass (slices of the
    same pass, same satellite within 10 minutes, are mosaicked)."""
    import ee
    pt = ee.Geometry.Point([lon, lat])
    area = pt.buffer(radius_m)
    s, e = start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

    def share(img, mask):
        stats = ee.Image.constant(1).updateMask(mask).unmask(0).rename("v").reduceRegion(
            ee.Reducer.mean(), area, 10, maxPixels=1e7)
        return ee.Feature(None, {"t": img.get("system:time_start"),
                                 "sat": img.get("platform_number"), "v": stats.get("v")})

    s1 = (ee.ImageCollection("COPERNICUS/S1_GRD").filterBounds(pt).filterDate(s, e)
          .filter(ee.Filter.eq("instrumentMode", "IW"))
          .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV")))
    s1f = s1.map(lambda im: share(im.set("platform_number", ee.String("S1").cat(im.get("platform_number"))),
                                  im.select("VV").mask()))

    s2 = ee.ImageCollection("COPERNICUS/S2_HARMONIZED").filterBounds(pt).filterDate(s, e)
    prob = ee.ImageCollection("COPERNICUS/S2_CLOUD_PROBABILITY").filterBounds(pt).filterDate(s, e)
    joined = ee.Join.saveFirst("cp").apply(s2, prob, ee.Filter.equals(leftField="system:index",
                                                                      rightField="system:index"))

    def s2share(im):
        im = ee.Image(im)
        cp = ee.Image(im.get("cp")).select("probability")
        clear = cp.lte(cloud_max).And(im.select("B4").mask())
        sat = ee.String("S2").cat(ee.String(im.get("SPACECRAFT_NAME")).slice(-1))
        return share(im.set("platform_number", sat), clear)

    s2f = ee.FeatureCollection(joined).map(s2share)
    rows = s1f.merge(s2f).getInfo()["features"]
    return group_passes([{"t_ms": r["properties"]["t"], "satellite": r["properties"]["sat"],
                          "v": r["properties"].get("v") or 0.0} for r in rows], min_valid)


def group_passes(rows, min_valid=C.MIN_VALID_SHARE, gap_min=10):
    """Pure: merge slices of one pass (same satellite, within gap_min minutes) taking the best share
    (an approximation of the mosaic, refined in the pilot), then apply the usable rule."""
    from datetime import datetime, timezone
    rows = sorted(rows, key=lambda r: (r["satellite"], r["t_ms"]))
    out = []
    for r in rows:
        t = datetime.fromtimestamp(r["t_ms"] / 1000, tz=timezone.utc)
        last = out[-1] if out else None
        if last and last["satellite"] == r["satellite"] and (t - last["time"]).total_seconds() <= gap_min * 60:
            last["valid_share"] = max(last["valid_share"], r["v"])
            last["usable"] = last["valid_share"] >= min_valid
            continue
        out.append({"time": t, "satellite": r["satellite"], "mission": r["satellite"][:2],
                    "valid_share": r["v"], "usable": r["v"] >= min_valid})
    return sorted(out, key=lambda a: a["time"])
