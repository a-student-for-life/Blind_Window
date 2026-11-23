"""Floodplain point next to the river cell (ANALYSIS_PLAN.md section 4), from Earth Engine.

Candidates: 30 m pixels in the 3 x 3 block of GloFAS cells around the river cell with JRC GSW
occurrence < 5 %, MERIT Hydro HAND <= 5 m, not ESA WorldCover built-up. Chosen: lowest HAND; ties
broken toward the cell centre (a 1e-3 m per km penalty, far below HAND's 0.1 m resolution in practice).
"""
from . import config as C

HALF = 0.075        # 1.5 GloFAS cells of 0.05 deg


def floodplain_point(lat, lon):
    import ee
    box = ee.Geometry.Rectangle([lon - HALF, lat - HALF, lon + HALF, lat + HALF])
    occ = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").unmask(0)
    hand = ee.Image("MERIT/Hydro/v1_0_1").select("hnd")
    wc = ee.ImageCollection("ESA/WorldCover/v100").first().select("Map")
    ok = occ.lt(C.GSW_MAX_OCCURRENCE).And(hand.lte(C.HAND_MAX_M)).And(wc.neq(C.WORLDCOVER_URBAN))
    import math
    ll = ee.Image.pixelLonLat()
    dist_km = ll.select("longitude").subtract(lon).multiply(111.32 * math.cos(math.radians(lat))).pow(2).add(
        ll.select("latitude").subtract(lat).multiply(110.57).pow(2)).sqrt()
    score = hand.add(dist_km.multiply(1e-3)).rename("score").updateMask(ok)
    img = score.addBands(hand.rename("hand")).addBands(ee.Image.pixelLonLat())
    r = img.reduceRegion(ee.Reducer.min(4), box, 30, maxPixels=1e8).getInfo()
    if not r or r.get("min") is None:
        return {"lat": None, "lon": None, "note": "no candidate pixel (exclusion 2)"}
    # Reducer.min(4): min of band 1 (score) plus bands 2-4 at that pixel, named min, min1, min2, min3
    return {"lat": r.get("min3"), "lon": r.get("min2"), "hand_m": r.get("min1"),
            "river_cell": [lat, lon], "raw": r}
