#!/usr/bin/env python3
"""
build_panel_all9.py  -  assemble the per-year, all-9-campus analysis panel.

Joins the admissions funnel (data/dv_admissions_all9.csv) to CAASPP grade-11 proficiency,
A-G eligibility (cohort + UC/CSU-eligible counts) and UPP/headcount, through the CEEB<->CDS
crosswalk, one row per (CEEB x campus x year). Year alignment mirrors the original
merge_panel.py: CAASPP uses the PRIOR year (Y-1) so each entering class is matched to its own
grade-11 test; A-G uses grad cohort (year-1)-(year);
UPP uses pupil year (year-1)-(year). CAASPP 2021 is excluded (COVID, non-representative).

Reproducible from the committed repo (no raw 12 GB needed).

Usage:  python scripts/build_panel_all9.py
"""
import csv, glob, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data"); C = os.path.join(DATA, "components")

xwalk = {}; xmeta = {}
for r in csv.DictReader(open(os.path.join(DATA, "ceeb_cds_crosswalk.csv"))):
    xwalk[r["ceeb"]] = r["cds14"]; xmeta[r["ceeb"]] = (r.get("match_method",""), r.get("match_score",""))

caaspp = {}
for fp in glob.glob(os.path.join(C, "caaspp_*.csv")):
    if "caaspp_2021" in fp: continue   # COVID year, excluded
    for r in csv.DictReader(open(fp)): caaspp[(r["cds14"], r["year"])] = r
ag = {}; cupc = {}
for r in csv.DictReader(open(os.path.join(C, "ag_eligibility.csv"))): ag[(r["cds14"], r["ag_year"])] = r
for r in csv.DictReader(open(os.path.join(C, "upp_lcff.csv"))):       cupc[(r["cds14"], r["cupc_year"])] = r

def f(x):
    try: return float(x)
    except: return None
def agk(y): y = int(y); return f"{y-1}-{str(y)[2:]}"
def cuk(y): y = int(y); return f"{y-1}-{y}"

cols = ["ceeb","cds14","campus","year","school_name","city","county",
        "applicants","admits","enrollees","admit_rate","app_gpa","adm_gpa","enr_gpa",
        "ela_pct_met","math_pct_met","avg_pct_met",
        "ag_cohort","ag_met_uccsu_count","enroll_9_12","upp_pct","lcff_plus",
        "match_method","match_score"]
rows = []
for r in csv.DictReader(open(os.path.join(DATA, "dv_admissions_all9.csv"))):
    yr = r["year"]
    if yr.isdigit() and int(yr) < 2015: continue   # analysis era; full funnel history is in dv_admissions_all9.csv
    ce = r["ceeb"]; cds = xwalk.get(ce, ""); mm, ms = xmeta.get(ce, ("", ""))
    app = f(r["applicants"]); adm = f(r["admits"]); enr = f(r["enrollees"])
    rate = round(100*adm/app, 2) if (app and adm is not None and app > 0) else ""
    C2 = caaspp.get((cds, str(int(yr)-1))) if (cds and yr.isdigit()) else None  # LAG: admission Fall-Y <- spring (Y-1) CAASPP (each class's own grade-11 test)
    ela = f(C2["ela_pct_met"]) if C2 else None; math = f(C2["math_pct_met"]) if C2 else None
    avg = round((ela+math)/2, 2) if (ela is not None and math is not None) else (ela if ela is not None else math)
    A = ag.get((cds, agk(yr))) if cds else None
    agc = f(A["ag_cohort"]) if A else None; agm = f(A["ag_met_uccsu_count"]) if A else None
    U = cupc.get((cds, cuk(yr))) if cds else None
    upp = f(U["upp_pct"]) if U else None; en912 = U["enroll_9_12"] if U else ""; lcff = U["lcff_plus_flag"] if U else ""
    rows.append([ce, cds, r["campus"], yr, r["school_name"], r["city"], r["county"],
        int(app) if app else "", int(adm) if adm is not None else "", int(enr) if enr is not None else "",
        rate, r.get("app_gpa",""), r.get("adm_gpa",""), r.get("enr_gpa",""),
        ela if ela is not None else "", math if math is not None else "", avg if avg is not None else "",
        int(agc) if agc else "", int(agm) if agm else "", en912, upp if upp is not None else "", lcff, mm, ms])

with open(os.path.join(DATA, "panel_all9_by_year.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(cols); w.writerows(rows)

# report
from collections import Counter
cc = Counter(r[2] for r in rows)
print("panel rows:", len(rows))
for camp in sorted(cc): print(f"  {camp:14} {cc[camp]}")
yrs = sorted(set(r[3] for r in rows if r[14] != ""))
print("years with CAASPP avg present:", ", ".join(yrs))
print("rows w/ enrollees:", sum(1 for r in rows if r[9] != ""),
      "| w/ eligible:", sum(1 for r in rows if r[16] != ""),
      "| w/ headcount:", sum(1 for r in rows if r[17] != ""))
