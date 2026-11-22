"""Check that the three accounts are set up, without printing any secret.

    python -m study.creds
"""
import importlib.util
import json
import os
from pathlib import Path

HOME = Path.home()


def check():
    rows = []
    cds = HOME / ".cdsapirc"
    if cds.exists():
        txt = cds.read_text(encoding="utf-8", errors="replace")
        ok = "ewds.climate.copernicus.eu" in txt and "key:" in txt
        rows.append(("EWDS (GloFAS) ~/.cdsapirc", ok, "found" if ok else "found, but url is not EWDS or key missing"))
    else:
        rows.append(("EWDS (GloFAS) ~/.cdsapirc", False, "missing"))

    ecm = HOME / ".ecmwfapirc"
    try:
        d = json.loads(ecm.read_text(encoding="utf-8"))
        ok = all(k in d for k in ("url", "key", "email"))
        rows.append(("ECMWF Web API (TIGGE) ~/.ecmwfapirc", ok, "found" if ok else "missing url/key/email"))
    except FileNotFoundError:
        rows.append(("ECMWF Web API (TIGGE) ~/.ecmwfapirc", False, "missing"))
    except ValueError:
        rows.append(("ECMWF Web API (TIGGE) ~/.ecmwfapirc", False, "not valid JSON"))

    if importlib.util.find_spec("ee") is None:
        rows.append(("Earth Engine", False, "earthengine-api not installed"))
    else:
        try:
            from .fetch import ee_key_file, init_ee
            ee = init_ee()
            ee.Number(1).getInfo()
            how = "service-account key" if ee_key_file() else "browser login"
            rows.append(("Earth Engine", True, f"initialised ({how})"))
        except Exception as e:  # report, never hide
            rows.append(("Earth Engine", False, f"init failed: {type(e).__name__}: {str(e)[:120]}"))

    for mod in ("cdsapi", "ecmwfapi", "numpy", "xarray"):
        rows.append((f"python package {mod}", importlib.util.find_spec(mod) is not None, ""))
    return rows


if __name__ == "__main__":
    for name, ok, note in check():
        print(f"{'OK ' if ok else 'NO '} {name:42s} {note}")
