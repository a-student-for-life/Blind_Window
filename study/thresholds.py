"""GloFAS v4 return-period thresholds (ANALYSIS_PLAN.md section 3).

The global threshold NetCDF files (one per return period, from the CEMS GloFAS auxiliary data)
are saved by hand or by the pilot into data/study/aux/ and are not committed. A file counts as the
threshold for return period N when its name contains `rl_N`, `rl_N.0`, `RP{N}`, `rp{N}` or `_{N}y`.
"""
import re
from functools import lru_cache
from pathlib import Path

AUX = Path(__file__).resolve().parent.parent / "data" / "study" / "aux"


def _matches(name, rp):
    pats = [rf"rl_{rp}(\.0)?\b", rf"rl_{rp}(\.0)?[_.]", rf"rp_?{rp}\b", rf"rp_?{rp}[_.]", rf"_{rp}y\b", rf"_{rp}y[_.]"]
    return any(re.search(p, name, re.I) for p in pats)


@lru_cache(maxsize=8)
def _dataset(rp):
    import xarray as xr
    files = [p for p in AUX.glob("*.nc") if _matches(p.name, rp)]
    if not files:
        from .pilot import NotReady
        raise NotReady(f"no {rp}-year GloFAS threshold file in {AUX} (expected a name containing rl_{rp})")
    return xr.open_dataset(files[0])


def rp_threshold(lat, lon, rp):
    ds = _dataset(rp)
    var = next(iter(ds.data_vars))
    latn = "latitude" if "latitude" in ds.coords else "lat"
    lonn = "longitude" if "longitude" in ds.coords else "lon"
    v = float(ds[var].sel({latn: lat, lonn: lon}, method="nearest"))
    return None if v != v else v
