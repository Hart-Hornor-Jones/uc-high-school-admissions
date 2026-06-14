#!/usr/bin/env python3
"""
parse_grad_rates.py - parse the UC Info Center "Freshman grad. rates by HS" dashboard
crosstabs into a tidy long CSV keyed by CEEB.

Source (Tableau crosstab downloads, one per UC-campus filter + one "All"):
  ug_outcomes_freshman_grad_rates_by_hs_internal_control/crosstabs/<campus>/high-school.csv
  Tab-delimited, CRLF. Columns: county ("X County"), CITY, SCHOOL NAME, entry year,
  1st-yr retention %, 4-yr grad %, 5-yr grad %, 6-yr grad %, Cohort Size.
  Universe: each row = the school's freshmen ENTERING UC in the fall of <entry year>
  (cohort shown only when N >= 10; rates are integer percents).
  Maturity: 6-yr rates exist through entry 2019, 5-yr through 2020, 4-yr through 2021,
  1st-yr retention through 2024 (as of the 2026 dashboard pull).

Matching: school names/cities/counties come from the SAME UC universe as the admissions
dimension table, so (name, city, county) matches CEEB nearly exactly. The handful of
keys mapping to >1 CEEB (school re-coded across eras) are assigned PER ENTRY YEAR to the
CEEB with the most DV enrollees that year (fallback: most enrollees overall).

Usage: python3 build/parse_grad_rates.py /path/to/ug_outcomes_..._internal_control
Writes: data/grad_rates_by_hs.csv (campus,ceeb,entry_year,cohort_n,ret1_pct,grad4_pct,grad5_pct,grad6_pct)
"""
import csv, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "..", "ug_outcomes_freshman_grad_rates_by_hs_internal_control")
CT = os.path.join(RAW, "crosstabs")

CAMPUS_DIR = {"all":"All","berkeley":"Berkeley","davis":"Davis","irvine":"Irvine",
  "los-angeles":"Los Angeles","merced":"Merced","riverside":"Riverside",
  "san-diego":"San Diego","santa-barbara":"Santa Barbara","santa-cruz":"Santa Cruz"}

def norm(s): return re.sub(r"[^A-Z0-9 ]", "", (s or "").upper()).strip()
def pct(s):
    s = (s or "").strip()
    return int(s[:-1]) if s.endswith("%") and s[:-1].isdigit() else None

# ---- dimension table: (name, city, county) -> {ceeb} ----
dim_path = os.path.join(REPO, "..", "admissions_source_school_consolidated_lean",
                        "admissions_freshman_school_dimension.csv")
if not os.path.exists(dim_path):
    dim_path = sys.argv[2]  # allow explicit path
idx = collections.defaultdict(set)
for d in csv.DictReader(open(dim_path, encoding="utf-8")):
    idx[(norm(d["school_name"]), norm(d["city"]), norm(d["county_state_country"]))].add(
        d["source_school_code_6"])

# ---- DV enrollee mass per (ceeb, year) and per ceeb, for disambiguation ----
e_by_cy = collections.Counter(); e_by_c = collections.Counter()
for r in csv.DictReader(open(os.path.join(DATA, "dv_admissions_all9.csv"), encoding="utf-8")):
    try: e = int(r["enrollees"])
    except (ValueError, TypeError): continue
    e_by_cy[(r["ceeb"], int(r["year"]))] += e; e_by_c[r["ceeb"]] += e

def pick(ceebs, year):
    if len(ceebs) == 1: return next(iter(ceebs)), "unique"
    best = max(ceebs, key=lambda c: (e_by_cy.get((c, year), 0), e_by_c.get(c, 0), c))
    return best, "by_year_activity"

out, unmatched, amb_log = [], collections.Counter(), collections.Counter()
for sub, campus in sorted(CAMPUS_DIR.items()):
    f = os.path.join(CT, sub, "high-school.csv")
    rows = list(csv.reader(open(f, encoding="utf-8", newline=""), delimiter="\t"))[1:]
    for r in rows:
        if len(r) < 9 or not r[3].strip().isdigit(): continue
        county, city, name, year = r[0], r[1], r[2], int(r[3])
        key = (norm(name), norm(city), norm(county).replace(" COUNTY", ""))
        ceebs = idx.get(key)
        if not ceebs:
            unmatched[(county, city, name)] += 1; continue
        ceeb, how = pick(ceebs, year)
        if how != "unique": amb_log[(name, city, tuple(sorted(ceebs)))] += 1
        n = int(r[8]) if r[8].strip().isdigit() else None
        out.append([campus, ceeb, year, n, pct(r[4]), pct(r[5]), pct(r[6]), pct(r[7])])

out.sort(key=lambda x: (x[0], x[1], x[2]))
os.makedirs(DATA, exist_ok=True)
dest = os.path.join(DATA, "grad_rates_by_hs.csv")
with open(dest, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    w.writerow(["campus","ceeb","entry_year","cohort_n","ret1_pct","grad4_pct","grad5_pct","grad6_pct"])
    w.writerows(out)

print(f"rows written: {len(out)}  ->  {dest}")
print(f"unmatched school keys: {len(unmatched)} ({sum(unmatched.values())} rows)")
for k, v in list(unmatched.items())[:10]: print("  MISS", k, v)
print(f"ambiguous keys resolved by yearly DV activity: {len(amb_log)}")
for k, v in amb_log.items(): print("  AMB ", k[0], k[1], "->", k[2], f"({v} rows)")
# sanity: campus 'All' coverage by year
ally = collections.Counter(r[2] for r in out if r[0] == "All")
print("All-UC rows/yr:", min(ally.values()), "-", max(ally.values()), "| years", min(ally), "-", max(ally))
