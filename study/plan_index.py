"""Historical ESA acquisition-plan index (ANALYSIS_PLAN.md section 6).

The yearly ZIPs from the SentiWiki document library are downloaded by hand or by the pilot into
data/study/plans_archive/ (not committed). This module indexes every plan file inside them.
Issue time = first timestamp of the file name; the pilot checks it against ZIP entry times.
"""
import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from blindwindow import plans as bw_plans

ARCHIVE = Path(__file__).resolve().parent.parent / "data" / "study" / "plans_archive"


def index(archive=ARCHIVE):
    rows = []
    for zp in sorted(Path(archive).glob("*.zip")):
        with zipfile.ZipFile(zp) as z:
            for info in z.infolist():
                m = bw_plans.NAME_RE.search(info.filename)
                if not m:
                    continue
                rows.append({
                    "satellite": m.group(1).upper(), "issued": bw_plans._dt(m.group(2)),
                    "valid_to": bw_plans._dt(m.group(3)), "zip": zp.name, "member": info.filename,
                    "zip_mtime": datetime(*info.date_time, tzinfo=timezone.utc)})
    # stray files (an S1B plan in an S1A zip) are kept: the satellite comes from the file name
    seen, out = set(), []
    for r in sorted(rows, key=lambda r: (r["satellite"], r["issued"], r["member"])):
        key = (r["satellite"], r["issued"], r["valid_to"])
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out


def load(row, archive=ARCHIVE):
    with zipfile.ZipFile(Path(archive) / row["zip"]) as z:
        data = z.read(row["member"])
    if data[:2] == b"PK" and not row["member"].lower().endswith((".kml", ".kmz")):
        with zipfile.ZipFile(io.BytesIO(data)) as inner:
            name = next(n for n in inner.namelist() if n.lower().endswith((".kml", ".kmz")))
            data = inner.read(name)
    return bw_plans.parse_kml(data, row["satellite"])
