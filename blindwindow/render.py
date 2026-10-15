"""Render one self-contained HTML page from the snapshot + 2024 replay evidence."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = Path(__file__).resolve().parent / "page.html"


def write(snapshot, path):
    replay = json.loads((ROOT / "data" / "replay_2024.json").read_text())
    series_path = ROOT / "data" / "guwahati_2024_reanalysis.json"
    series = json.loads(series_path.read_text()) if series_path.exists() else None
    payload = json.dumps({"snapshot": snapshot, "replay": replay, "series": series})
    html = TEMPLATE.read_text().replace("/*__DATA__*/null", payload.replace("</", "<\\/"))
    Path(path).write_text(html)
    return path
