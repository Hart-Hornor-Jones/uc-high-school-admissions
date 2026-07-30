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
OUT  = sys.argv[2] if len(sys.argv) > 2 else "data/dv_admissions_all9.csv"

CAMPUS = {"Berkeley","Davis","Irvine","Los Angeles","Merced",
          "Riverside","San Diego","Santa Barbara","Santa Cruz"}

# The coverage file's reconstructed `campus` labels assume the COUNTS tabs' campus ordering
# (Berkeley ... Santa Cruz, Universitywide LAST). The fr-gpa-by-yr tab's campus control lists
# Universitywide FIRST, so on that tab every label is shifted one position: the state labelled
# "Berkeley" is actually Universitywide, "Davis" is Berkeley, ..., "Universitywide" is Santa Cruz.
# Verified per (school-type x fall-term) block two ways -- school-count fingerprint and
# selectivity signature; see build/repair_gpa_offset_20260730.py for the full record.
COUNTS_ORDER = ["Berkeley","Davis","Irvine","Los Angeles","Merced",
                "Riverside","San Diego","Santa Barbara","Santa Cruz","Universitywide"]
GPA_ORDER    = ["Universitywide"] + COUNTS_ORDER[:-1]          # actual fr-gpa-by-yr control order
GPA_RELABEL  = dict(zip(COUNTS_ORDER, GPA_ORDER))              # coverage label -> actual campus

def load_keys(tab, relabel=None):
    keys = {}
    for r in csv.DictReader(open(f"{LEAN}/admissions_freshman_state_coverage.csv", encoding="utf-8")):
        if (r["source_tab"] == tab
                and r["school_type"] == "California public high school" and r["present"] == "True"):
            campus = relabel[r["campus"]] if relabel else r["campus"]
            if campus in CAMPUS:
                keys[r["state_key"]] = (campus, r["fall_term"])
    return keys

eth = load_keys("fr-eth-by-yr")
gpa = load_keys("fr-gpa-by-yr", relabel=GPA_RELABEL)
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

# ---- validation of the GPA relabel, per (campus x year) block ----
# (1) school-count fingerprint: schools with an applicant GPA nearly equal schools with an
#     applicant COUNT for the same campus+year (counts labels are known-correct); a residual
#     shift puts them off by 100+.  (2) selectivity signature: the share of GPA schools with
#     an ADMIT GPA must track campus admit rate (Berkeley/Los Angeles lowest, Merced highest).
gpa_app = defaultdict(set); gpa_adm = defaultdict(set); cnt_app = defaultdict(set)
for (ceeb, campus, year), g in gpaval.items():
    if "applicants" in g: gpa_app[(campus, year)].add(ceeb)
    if "admits" in g:     gpa_adm[(campus, year)].add(ceeb)
for (ceeb, campus, year), sc in counts.items():
    if sc.get("applicants"): cnt_app[(campus, year)].add(ceeb)
devs = sorted(((abs(len(gpa_app[k]) - len(cnt_app[k])), k) for k in gpa_app if k in cnt_app), reverse=True)
if devs:
    d, k = devs[0]
    sys.stderr.write(f"fingerprint: {len(devs)} campus-year blocks, max |gpa_schools - count_schools| = {d} at {k}\n")
    if d > 10: sys.stderr.write("  WARNING: fingerprint deviation > 10 -- GPA campus mapping suspect!\n")
for yr in ("2019", "2024"):
    sh = {cm: (len(gpa_adm[(cm, yr)] & gpa_app[(cm, yr)]), len(gpa_app[(cm, yr)]))
          for cm in CAMPUS if len(gpa_app[(cm, yr)]) > 100}
    if len(sh) < 9: continue
    pct = {cm: a / b for cm, (a, b) in sh.items()}
    low2 = sorted(pct, key=pct.get)[:2]; hi = max(pct, key=pct.get)
    ok = set(low2) == {"Berkeley", "Los Angeles"} and hi == "Merced"
    sys.stderr.write(f"selectivity {yr}: lowest admit-GPA coverage {sorted(low2)}, highest {hi} -> "
                     + ("OK\n" if ok else "WARNING: expected Berkeley/Los Angeles lowest, Merced highest\n"))
