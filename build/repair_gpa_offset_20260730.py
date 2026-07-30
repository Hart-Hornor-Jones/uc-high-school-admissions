#!/usr/bin/env python3
"""
repair_gpa_offset_20260730.py -- surgical repair of the fr-gpa-by-yr campus offset
in data/dv_admissions_all9.csv.

THE DEFECT (found 2026-07-25, repaired here 2026-07-30): the coverage file's
reconstructed `campus` labels assume the COUNTS tabs' campus ordering (Berkeley ...
Santa Cruz, Universitywide LAST), but the fr-gpa-by-yr tab's campus control lists
Universitywide FIRST. So on that tab every label is shifted one position within each
(school type x fall term) block: the state labelled "Berkeley" is actually
Universitywide, "Davis" is Berkeley, ..., "Universitywide" is Santa Cruz.
extract_dv_all9.py therefore attached each campus's app_gpa/adm_gpa/enr_gpa to the
wrong campus. Counts columns came from the counts tabs (labels verified correct) and
are untouched.

WHAT THIS SCRIPT DOES: re-extracts the three GPA columns from the lean GPA long file
with the corrected campus mapping and rewrites ONLY those columns of
data/dv_admissions_all9.csv in place (backup kept alongside; do not commit the
backup). The 503 MB counts long file is never read.

VALIDATION (all hard-checked before the file is written):
  V1 block order      -- within every (school type x fall term) coverage block the
                         labels run exactly Berkeley..Santa Cruz,Universitywide by
                         state_number, so the dict relabel == the one-position shift.
  V2 reproduction     -- the OLD file's GPA columns are reproduced exactly from the
                         re-extraction under the SHIFTED labels on all rows (proves
                         this re-extraction is bit-identical to the original run;
                         the relabel is then the only change). Includes the known
                         identity: corrected-Universitywide GPA == old "Berkeley"
                         column on every Berkeley row that carries GPA.
  V3 fingerprint      -- per (campus x year): #schools with an applicant GPA tracks
                         #schools with an applicant COUNT (counts labels correct);
                         a residual shift would put blocks off by 100+.
  V4 selectivity      -- share of GPA schools with an ADMIT GPA tracks campus admit
                         rate: Berkeley/Los Angeles lowest, Merced highest (checked
                         fall 2019 and fall 2024).

IDEMPOTENT: if the file already matches the CORRECTED extraction it is left alone.

Usage:
  python build/repair_gpa_offset_20260730.py /path/to/admissions_source_school_consolidated_lean \
         [data/dv_admissions_all9.csv]
"""
import csv, os, sys
from collections import defaultdict

LEAN = sys.argv[1] if len(sys.argv) > 1 else "path/to/admissions_source_school_consolidated_lean"
DV   = sys.argv[2] if len(sys.argv) > 2 else "data/dv_admissions_all9.csv"
BACKUP = DV.replace(".csv", "_pre_gpa_repair_20260730.csv")

CAMPUS = {"Berkeley","Davis","Irvine","Los Angeles","Merced",
          "Riverside","San Diego","Santa Barbara","Santa Cruz"}
COUNTS_ORDER = ["Berkeley","Davis","Irvine","Los Angeles","Merced",
                "Riverside","San Diego","Santa Barbara","Santa Cruz","Universitywide"]
GPA_ORDER    = ["Universitywide"] + COUNTS_ORDER[:-1]          # actual fr-gpa-by-yr control order
GPA_RELABEL  = dict(zip(COUNTS_ORDER, GPA_ORDER))              # coverage label -> actual campus

def fail(msg):
    sys.stderr.write(f"FAIL: {msg}\n"); sys.exit(1)

# ---- V1: coverage block order, then state_key -> (actual campus, year) ----
blocks = defaultdict(list)   # (school_type, fall_term) -> [(state_number, label, present)]
for r in csv.DictReader(open(f"{LEAN}/admissions_freshman_state_coverage.csv", encoding="utf-8")):
    if r["source_tab"] == "fr-gpa-by-yr":
        blocks[(r["school_type"], r["fall_term"])].append(
            (int(r["state_number"]), r["campus"], r["present"], r["state_key"]))
keymap = {}          # state_key -> (actual campus incl. Universitywide, year)  [CA public only]
for (stype, term), rows in sorted(blocks.items()):
    rows.sort()
    labels = [b[1] for b in rows]
    if labels != COUNTS_ORDER[:len(labels)]:
        fail(f"V1 block order broken in ({stype}, {term}): {labels}")
    if stype != "California public high school":
        continue
    for _, label, present, sk in rows:
        if present == "True":
            keymap[sk] = (GPA_RELABEL[label], term)
print(f"V1 OK: {len(blocks)} coverage blocks in counts-label order; "
      f"{len(keymap)} CA-public GPA states mapped")

# ---- dimension: school_id -> ceeb ----
dim = {}
for r in csv.DictReader(open(f"{LEAN}/admissions_freshman_school_dimension.csv", encoding="utf-8")):
    dim[r["school_id"]] = r["source_school_code_6"]

# ---- re-extract GPA under the CORRECTED mapping (same last-row-wins semantics
#      as extract_dv_all9.py; statuses: applicants / admits / enrollees) ----
val = defaultdict(dict)      # (ceeb, actual campus, year) -> {status: float}
with open(f"{LEAN}/admissions_freshman_gpa_observed_long.csv", encoding="utf-8") as f:
    next(f)
    for line in f:
        p = line.rstrip("\n").split(",")
        if len(p) != 6: continue
        m = keymap.get(p[0])
        if not m: continue
        ce = dim.get(p[1])
        if not ce: continue
        try: val[(ce, m[0], m[1])][p[4]] = float(p[5])
        except ValueError: pass
print(f"re-extracted GPA cells: {sum(len(v) for v in val.values())} across {len(val)} school-campus-years")

def fmt(x):
    return "" if x is None else f"{x:.2f}"
def newg(ce, campus, yr):
    g = val.get((ce, campus, yr), {})
    return [fmt(g.get("applicants")), fmt(g.get("admits")), fmt(g.get("enrollees"))]
def oldg(ce, campus, yr):
    # what the pre-repair pipeline attached: the state LABELLED `campus`, i.e. the
    # actual campus GPA_RELABEL[campus]
    return newg(ce, GPA_RELABEL[campus], yr)

# ---- read the dv file; decide state; V2 ----
with open(DV, newline="", encoding="utf-8") as f:
    rd = csv.reader(f); header = next(rd); rows = list(rd)
if header[:9] != ["ceeb","campus","year","applicants","admits","enrollees","app_gpa","adm_gpa","enr_gpa"]:
    fail(f"unexpected dv header: {header}")

match_shift = match_corr = 0; mism = []
n_gpa_old = 0; berk_id = [0, 0]
for r in rows:
    ce, campus, yr = r[0], r[1], r[2]
    cur = [r[6], r[7], r[8]]
    if cur == oldg(ce, campus, yr): match_shift += 1
    if cur == newg(ce, campus, yr): match_corr += 1
    if any(cur): n_gpa_old += 1
    if campus == "Berkeley" and any(cur):
        berk_id[1] += 1
        if cur == newg(ce, "Universitywide", yr): berk_id[0] += 1

if match_corr == len(rows):
    print(f"already repaired: all {len(rows)} rows match the corrected extraction; nothing to do")
    sys.exit(0)
if match_shift != len(rows):
    bad = len(rows) - match_shift
    for r in rows:
        if [r[6], r[7], r[8]] != oldg(r[0], r[1], r[2]):
            mism.append(r[:3] + r[6:9]);
            if len(mism) >= 5: break
    fail(f"V2 reproduction: {bad}/{len(rows)} rows do NOT match the shifted re-extraction "
         f"(file neither pristine-shifted nor corrected). First mismatches: {mism}")
print(f"V2 OK: all {len(rows)} rows' GPA columns reproduced under shifted labels "
      f"({n_gpa_old} rows carry GPA); corrected-Universitywide == old-'Berkeley' on "
      f"{berk_id[0]}/{berk_id[1]} Berkeley GPA rows")
if berk_id[0] != berk_id[1]:
    fail("V2 identity: corrected-Universitywide GPA does not equal the old 'Berkeley' column")

# ---- V3: school-count fingerprint per (campus, year) ----
gpa_app = defaultdict(set); gpa_adm = defaultdict(set); cnt_app = defaultdict(set)
for (ce, campus, yr), g in val.items():
    if "applicants" in g: gpa_app[(campus, yr)].add(ce)
    if "admits" in g:     gpa_adm[(campus, yr)].add(ce)
for r in rows:
    if r[3]: cnt_app[(r[1], r[2])].add(r[0])
devs = sorted(((abs(len(gpa_app[k]) - len(cnt_app[k])), k)
               for k in gpa_app if k[0] in CAMPUS and k in cnt_app), reverse=True)
dmax, kmax = devs[0]
print(f"V3 fingerprint: {len(devs)} campus-year blocks; max |gpa_schools - count_schools| = {dmax} at {kmax}")
if dmax > 10:
    fail("V3 fingerprint deviation > 10 -- GPA campus mapping suspect")

# ---- V4: selectivity signature ----
for yr in ("2019", "2024"):
    pct = {}
    for cm in CAMPUS:
        n = len(gpa_app[(cm, yr)])
        if n > 100: pct[cm] = len(gpa_adm[(cm, yr)] & gpa_app[(cm, yr)]) / n
    if len(pct) < 9: continue
    low2 = sorted(pct, key=pct.get)[:2]; hi = max(pct, key=pct.get)
    tbl = "  ".join(f"{cm}:{100*pct[cm]:.1f}%" for cm in sorted(pct, key=pct.get))
    print(f"V4 selectivity {yr}: {tbl}")
    if set(low2) != {"Berkeley", "Los Angeles"} or hi != "Merced":
        fail(f"V4 selectivity {yr}: expected Berkeley/Los Angeles lowest and Merced highest, "
             f"got lowest {low2}, highest {hi}")
print("V4 OK: admit-GPA coverage tracks campus selectivity")

# ---- write: backup, then replace ONLY the three GPA columns ----
if not os.path.exists(BACKUP):
    os.replace(DV, BACKUP)
else:
    fail(f"backup already exists: {BACKUP} (refusing to overwrite)")
changed = 0
with open(DV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(header)
    for r in rows:
        g = newg(r[0], r[1], r[2])
        if g != [r[6], r[7], r[8]]: changed += 1
        w.writerow(r[:6] + g + r[9:])
print(f"wrote {DV}: {len(rows)} rows, GPA columns changed on {changed}; backup at {BACKUP}")
print("NOTE: do not commit the backup file.")
