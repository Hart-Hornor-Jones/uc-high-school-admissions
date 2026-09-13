#!/usr/bin/env python3
"""
build_school_locations.py  -  slim per-school coordinates for the site (data/components/school_locations.csv).

Source: the CDE Public Schools & Districts directory (pubschls), which carries a latitude/longitude
for each CDS record. The hs-data context pipeline joins that directory to the CAASPP school universe
and writes `ca_school_context_out/ca_school_cde_location_by_cds.csv` (one row per CDS code, with
`cde_latitude`, `cde_longitude`, `cde_location_quality`). This script keeps only the schools that
appear in the CEEB<->CDS crosswalk and only the two coordinate columns, so the repo rebuilds the
distance metric without the upstream file.

The site uses the coordinates for one thing: the straight-line (great-circle) distance from each
school to the selected campus, computed client-side against the campus coordinates listed in
scripts/make_site_data.py.

Usage:  python3 build/build_school_locations.py /path/to/ca_school_cde_location_by_cds.csv
"""
import csv, os, sys

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data"); COMP = os.path.join(DATA, "components")

src = sys.argv[1] if len(sys.argv) > 1 else None
if not src or not os.path.exists(src):
    sys.exit("usage: build_school_locations.py /path/to/ca_school_cde_location_by_cds.csv")

wanted = set()
for r in csv.DictReader(open(os.path.join(DATA, "ceeb_cds_crosswalk.csv"), encoding="utf-8")):
    c = (r.get("cds14") or "").strip()
    if c.isdigit(): wanted.add(c.zfill(14))

out = {}
for r in csv.DictReader(open(src, encoding="utf-8", errors="replace")):
    c = (r.get("cds_code") or "").strip().zfill(14)
    if c not in wanted: continue
    try: lat = float(r["cde_latitude"]); lon = float(r["cde_longitude"])
    except (ValueError, KeyError, TypeError): continue
    if not (32 <= lat <= 42.5 and -125 <= lon <= -114): continue   # inside California
    out[c] = (round(lat, 5), round(lon, 5))

os.makedirs(COMP, exist_ok=True)
with open(os.path.join(COMP, "school_locations.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["cds14", "latitude", "longitude"])
    for c in sorted(out): w.writerow([c, out[c][0], out[c][1]])
print(f"school_locations.csv: {len(out)} of {len(wanted)} crosswalked CDS codes carry coordinates")
