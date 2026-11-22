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


def glofas_forecast_request(issue_date, lat, lon, max_lead_h=720):
    return ("cems-glofas-forecast", {
        "system_version": ["operational"], "hydrological_model": ["lisflood"],
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
