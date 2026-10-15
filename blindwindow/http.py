"""Small HTTP helper: GET with retries, on-disk cache, and a request log."""
import hashlib
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

from .config import HTTP_TIMEOUT

CACHE_DIR = Path(__file__).resolve().parent.parent / "data" / "cache"
LOG = []


def get(url, params=None, cache=True, retries=2, binary=False):
    if params:
        url = url + "?" + urllib.parse.urlencode(params, safe=",")
    key = hashlib.sha1(url.encode()).hexdigest()
    path = CACHE_DIR / key
    if cache and path.exists():
        LOG.append({"url": url, "status": "cache"})
        data = path.read_bytes()
        return data if binary else data.decode("utf-8", "replace")

    last_err = None
    for attempt in range(retries + 1):
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "blind-window/0.1"})
            with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
                data = r.read()
            LOG.append({"url": url, "status": 200, "ms": round((time.time() - t0) * 1000)})
            if cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            return data if binary else data.decode("utf-8", "replace")
        except Exception as e:  # report real errors, never invent data
            last_err = e
            LOG.append({"url": url, "status": "error", "error": repr(e), "attempt": attempt})
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed after retries: {url}: {last_err!r}")


def get_json(url, params=None, cache=True):
    return json.loads(get(url, params, cache=cache))
