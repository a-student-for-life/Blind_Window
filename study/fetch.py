"""Data requests. Each builder returns a plain dict so tests can check it without the network;
the retrieve_* functions import their client lazily. Not yet run against the servers: the pilot is
their first test (field names may need fixing there, recorded in pilot/PILOT_NOTES.md).

Credentials are read by the clients from the user's home folder, never from this repo:
  ~/.cdsapirc     EWDS (GloFAS): url: https://ewds.climate.copernicus.eu/api  key: <token>
  ~/.ecmwfapirc   ECMWF Web API (TIGGE): {"url": ..., "key": ..., "email": ...}
  Earth Engine    a service-account key file at ~/ee-key.json (or EE_KEY_FILE=<path>), or
                  `earthengine authenticate` once; plus EE_PROJECT=<cloud project id>
"""
import os
from pathlib import Path

EWDS_URL = "https://ewds.climate.copernicus.eu/api"
TIGGE_TCC = "228164"
ASF_SEARCH = "https://api.daac.asf.alaska.edu/services/search/param"


def _area(lat, lon, half=0.15):
    return [round(lat + half, 3), round(lon - half, 3), round(lat - half, 3), round(lon + half, 3)]  # N W S E


def glofas_reanalysis_request(year, lat, lon):
    return ("cems-glofas-historical", {
        "system_version": ["version_4_0"], "hydrological_model": ["lisflood"],
        "product_type": ["consolidated"], "timespan": ["time_mean"],
        "variable": ["average_river_discharge_in_the_last_24_hours"],
        "year": [str(year)], "month": [f"{m:02d}" for m in range(1, 13)],
        "day": [f"{d:02d}" for d in range(1, 32)],
        "data_format": "netcdf", "download_format": "unarchived", "area": _area(lat, lon)})


GLOFAS_V4_FORECAST_START = "2021-05-26"   # before this date the archive holds htessel_lisflood (0.1 deg)


def glofas_forecast_request(issue_date, lat, lon, max_lead_h=720):
    model = "lisflood" if issue_date.isoformat() >= GLOFAS_V4_FORECAST_START else "htessel_lisflood"
    return ("cems-glofas-forecast", {
        "system_version": ["operational"], "hydrological_model": [model],
        "product_type": ["control_forecast", "ensemble_perturbed_forecasts"],
        "variable": ["river_discharge_in_the_last_24_hours"],
        "year": [str(issue_date.year)], "month": [f"{issue_date.month:02d}"], "day": [f"{issue_date.day:02d}"],
        "leadtime_hour": [str(h) for h in range(24, max_lead_h + 1, 24)],
        "data_format": "netcdf", "download_format": "unarchived", "area": _area(lat, lon)})


def tigge_tcc_request(issue_date, lat, lon, target):
    return {"class": "ti", "dataset": "tigge", "expver": "prod", "origin": "ecmf", "levtype": "sfc",
            "param": TIGGE_TCC, "type": "pf", "number": "1/to/50", "time": "00:00:00",
            "date": issue_date.strftime("%Y-%m-%d"), "step": "/".join(str(s) for s in range(0, 361, 6)),
            "grid": "0.5/0.5", "area": "/".join(str(x) for x in _area(lat, lon, 0.5)),
            "format": "netcdf", "target": str(target)}


def asf_s1_request(lat, lon, start, end, level="RAW"):
    return (ASF_SEARCH, {"platform": "SENTINEL-1", "beamMode": "IW", "processingLevel": level,
                         "intersectsWith": f"POINT({lon} {lat})", "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                         "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"), "output": "geojson", "maxResults": 2000})


def retrieve_ewds(dataset_and_request, target):
    import cdsapi
    dataset, req = dataset_and_request
    cdsapi.Client(url=EWDS_URL).retrieve(dataset, req, str(target))
    return Path(target)


def retrieve_tigge(req):
    from ecmwfapi import ECMWFDataServer
    ECMWFDataServer().retrieve(req)
    return Path(req["target"])


def ee_key_file():
    p = Path(os.environ.get("EE_KEY_FILE", Path.home() / "ee-key.json"))
    return p if p.exists() else None


def init_ee():
    """Service-account key if present (works where the browser login is blocked), else the
    stored `earthengine authenticate` login."""
    import json
    import ee
    key = ee_key_file()
    project = os.environ.get("EE_PROJECT")
    if key:
        info = json.loads(key.read_text(encoding="utf-8"))
        creds = ee.ServiceAccountCredentials(info["client_email"], str(key))
        ee.Initialize(creds, project=project or info["project_id"])
        return ee
    if not project:
        raise RuntimeError("Set EE_PROJECT to your Earth Engine Cloud project id, or save a key as ~/ee-key.json")
    ee.Initialize(project=project)
    return ee


# ---------------------------------------------------------------- TIGGE from the ECMWF Data Store
# DEVIATIONS.md #1: TIGGE moved to ECDS on 27 May 2026. Key file: ~/.ecdsapirc (url + key, the
# same two-line format as ~/.cdsapirc). ECDS serves TIGGE as GRIB only, all 50 members.

ECDS_URL = "https://ecds.ecmwf.int/api"
ECDS_RC = Path.home() / ".ecdsapirc"


def tigge_tcc_request_ecds(issue_date, lat, lon, max_step_h=360, steps=None):
    """Field names from the ECDS form (catalogue/v1/collections/tigge-forecasts/form.json).
    The form has no member choice: all 50 perturbed members come back."""
    steps = range(0, max_step_h + 1, 6) if steps is None else steps
    return ("tigge-forecasts", {
        "origin": "ecmwf", "level_type": "single_level", "forecast_type": "perturbed_forecast",
        "variable": ["total_cloud_cover"],
        "year": str(issue_date.year), "month": f"{issue_date.month:02d}", "day": f"{issue_date.day:02d}",
        "time": "00:00", "leadtime_hour": [str(s) for s in steps],
        "area": _area(lat, lon, 0.5), "data_format": "grib"})


def retrieve_tigge_ecds(issue_date, lat, lon, target, request=None):
    """request: override (dataset, dict) when the ECDS field names differ from the guess above."""
    import cdsapi
    if not ECDS_RC.exists():
        raise FileNotFoundError(f"{ECDS_RC} missing: save url and key of the ECMWF Data Store there")
    cfg = dict(line.split(":", 1) for line in ECDS_RC.read_text(encoding="utf-8").splitlines() if ":" in line)
    dataset, req = request or tigge_tcc_request_ecds(issue_date, lat, lon)
    cdsapi.Client(url=cfg["url"].strip(), key=cfg["key"].strip()).retrieve(dataset, req, str(target))
    return Path(target)


def tigge_point_series(path, lat, lon, tau):
    """[(valid_time, ensemble-mean tcc %)] at the grid point nearest (lat, lon)."""
    from datetime import timedelta
    import numpy as np
    import xarray as xr
    ds = xr.open_dataset(path, engine="cfgrib", backend_kwargs={"indexpath": ""})
    var = next(v for v in ds.data_vars if "tcc" in v.lower() or "cloud" in v.lower())
    s = ds[var].sel(latitude=lat, longitude=lon, method="nearest")
    if "number" in s.dims:
        s = s.mean("number")
    scale = 100.0 if float(s.max()) <= 1.0001 else 1.0
    out = []
    for st, v in zip(s["step"].values, s.values):
        hours = float(np.timedelta64(st, "ns") / np.timedelta64(1, "h"))
        out.append((tau + timedelta(hours=hours), float(v) * scale))
    return sorted(out)
