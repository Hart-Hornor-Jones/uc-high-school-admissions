#!/usr/bin/env python3
"""
extract_dv_all9.py  -  per-school x campus x year admissions funnel, all 9 campuses.

Reads the consolidated UC Information Center "by source school" dump
(admissions_source_school_consolidated_lean/, ~558 MB, NOT committed) and writes a
compact long file: one row per (CEEB, campus, year) with applicants/admits/enrollees
(+ applicant/admit/enrollee GPA where reported). This is the only step that needs the large raw source;
its output (data/dv_admissions_all9.csv) IS committed, so the rest of the pipeline runs
without the raw files.

Logic mirrors the prior project's extract_dv_all.py (subgroup="All" totals from the
race/ethnicity tab; California public high schools only).

Usage:  python build/extract_dv_all9.py /path/to/admissions_source_school_consolidated_lean
"""
import csv, sys
from collections import defaultdict

LEAN = sys.argv[1] if len(sys.argv) > 1 else \
    "path/to/admissions_source_school_consolidated_lean"
OUT  = sys.argv[2] if len(sys.argv) > 2 else \
    "/sessions/serene-practical-tesla/mnt/outputs/uc-merit-admissions/data/dv_admissions_all9.csv"

CAMPUS = {"Berkeley","Davis","Irvine","Los Angeles","Merced",
          "Riverside","San Diego","Santa Barbara","Santa Cruz"}

def load_keys(tab):
    keys = {}
    for r in csv.DictReader(open(f"{LEAN}/admissions_freshman_state_coverage.csv", encoding="utf-8")):
        if (r["source_tab"] == tab and r["campus"] in CAMPUS
                and r["school_type"] == "California public high school" and r["present"] == "True"):
            keys[r["state_key"]] = (r["campus"], r["fall_term"])
    return keys

eth = load_keys("fr-eth-by-yr")
gpa = load_keys("fr-gpa-by-yr")
sys.stderr.write(f"eth_keys={len(eth)} gpa_keys={len(gpa)}\n")

dim = {}
for r in csv.DictReader(open(f"{LEAN}/admissions_freshman_school_dimension.csv", encoding="utf-8")):
    dim[r["school_id"]] = (r["source_school_code_6"], r["school_name"], r["city"], r["county_state_country"])

counts = defaultdict(lambda: defaultdict(float))   # (ceeb,campus,year) -> status -> count
meta = {}; miss = 0
with open(f"{LEAN}/admissions_freshman_counts_observed_long.csv", encoding="utf-8") as f:
    next(f)
    for line in f:
        p = line.rstrip("\n").split(",")
        if len(p) != 8: continue
        sk = p[0]
        if sk not in eth: continue
        if p[5] != "race_ethnicity" or p[6] != "All": continue
        d = dim.get(p[1])
        if not d: miss += 1; continue
        ceeb = d[0]; campus, year = eth[sk]
        counts[(ceeb, campus, year)][p[4]] += float(p[7]); meta[(ceeb, campus, year)] = (d[1], d[2], d[3])

gpaval = defaultdict(dict)
with open(f"{LEAN}/admissions_freshman_gpa_observed_long.csv", encoding="utf-8") as f:
    next(f)
    for line in f:
        p = line.rstrip("\n").split(",")
        if len(p) != 6: continue
        sk = p[0]
        if sk not in gpa: continue
        d = dim.get(p[1])
        if not d: continue
        campus, year = gpa[sk]
        try: gpaval[(d[0], campus, year)][p[4]] = float(p[5])
        except: pass

out = []
for k, sc in counts.items():
    ceeb, campus, year = k; nm, city, county = meta[k]; g = gpaval.get(k, {})
    out.append([ceeb, campus, year,
                int(sc.get("applicants", 0)) or "", int(sc.get("admits", 0)) or "", int(sc.get("enrollees", 0)) or "",
                g.get("applicants", ""), g.get("admits", ""), g.get("enrollees", ""), nm, city, county])
out.sort(key=lambda r: (r[1], r[2], r[0]))
with open(OUT, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["ceeb","campus","year","applicants","admits","enrollees","app_gpa","adm_gpa","enr_gpa","school_name","city","county"])
    w.writerows(out)

from collections import Counter
c = Counter(r[1] for r in out)
sys.stderr.write(f"dim_miss={miss} rows={len(out)}\n")
for camp in sorted(CAMPUS): sys.stderr.write(f"  {camp:14} rows={c[camp]}\n")
