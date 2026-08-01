#!/usr/bin/env python3
"""Independent verification twin for history/data_history.js.

Re-derives the page's key displayed statistics from the source files by a
separate code path (no reuse of build_history_data.py functions) and compares
them to the shipped data file. Exit code 0 = every check passes.

Usage mirrors the builder:
  python verify_history_anchors.py --panel ... --spine ... --star-panel ...
      --syw ... --analysis ... --data history/data_history.js
"""
import argparse, json, re, sys
import pandas as pd, numpy as np
from scipy import stats

ap = argparse.ArgumentParser()
ap.add_argument("--panel", required=True)
ap.add_argument("--spine", required=True)
ap.add_argument("--star-panel", required=True)
ap.add_argument("--syw", required=True)
ap.add_argument("--analysis", required=True)
ap.add_argument("--data", required=True, help="the shipped data_history.js")
A = ap.parse_args()

raw = open(A.data, encoding="utf-8").read()
D = json.loads(re.search(r"window\.HISTORY_DATA = (\{.*\});", raw, re.S).group(1))

PASS = []
def check(name, got, want, tol=0.0005):
    okv = abs(got - want) <= tol if isinstance(want, float) else got == want
    PASS.append(okv)
    print(("  ok  " if okv else "FAIL  ") + f"{name}: recomputed {got} vs shipped {want}")

print("loading sources ...")
syw = pd.read_csv(A.syw, dtype={"ceeb": str}, low_memory=False)
syw["ceeb"] = syw.ceeb.str.zfill(6)
panel = pd.read_csv(A.panel, dtype={"cds14": str, "ceeb": str}, low_memory=False)

# --- 1. Berkeley 2016 college-bound anchor, from raw panel + admit rates ----
t = panel[panel.ceeb.notna()].copy(); t["ceeb"] = t.ceeb.str.zfill(6)
t16 = t[t.uc_cycle_year == 2016][["ceeb", "z_sat_primary"]]
s16 = syw[syw.year == 2016]
j = s16.merge(t16, on="ceeb", how="left")
j = j[j.berk_applicants >= 25][["berk_admit_rate", "z_sat_primary"]].dropna()
r = stats.pearsonr(j.berk_admit_rate, j.z_sat_primary)[0]
check("Berkeley 2016 college-bound r", round(r, 4), D["anchors"]["berkeley_2016_sat_r"])
check("Berkeley 2016 n schools", len(j), D["anchors"]["berkeley_2016_sat_n"])

# --- 2. census arc on the graduating-class axis, recomputed independently ---
# Deliberately a separate code path: read each instrument straight from the
# STAR/CAHSEE panel at its own grade, apply the cohort offset by hand, and
# recompute. Offsets asserted here, not imported from the builder.
OFFSET = {"caaspp": 1, "cst11": 1, "cahsee": 2, "s9": 2}
COL = {"cst11": "star_ela_g11_pct_prof_plus", "cahsee": "cahsee_ela_pct_passed_census",
       "s9": "star_s9_read_pac50"}
stp = pd.read_csv(A.star_panel, dtype={"cds14": str, "ceeb": str}, low_memory=False,
                  usecols=["ceeb", "uc_cycle_year"] + list(COL.values()))
stp = stp[stp.ceeb.notna()].copy(); stp["ceeb"] = stp.ceeb.str.zfill(6)

def recompute(pref, cls_year, src):
    if src == "caaspp":
        t = syw[syw.year == cls_year - OFFSET[src]][["ceeb", "avg_pct_met"]].rename(
            columns={"avg_pct_met": "v"})
    else:
        t = stp[stp.uc_cycle_year == cls_year - OFFSET[src]][["ceeb", COL[src]]].rename(
            columns={COL[src]: "v"})
    t = t.dropna()
    ss = syw[syw.year == cls_year]
    jj = ss.merge(t, on="ceeb", how="left")
    jj = jj[jj[f"{pref}_applicants"] >= 25][[f"{pref}_admit_rate", "v"]].dropna()
    return round(stats.pearsonr(jj[f"{pref}_admit_rate"], jj.v)[0], 4), len(jj)

shipped = {c: {(p[0], p[3]): (p[1], p[2], p[4]) for p in D["arc"][c]["census"]} for c in D["arc"]}
for camp, pref in [("Berkeley", "berk"), ("Riverside", "riverside"), ("San Diego", "sd"),
                   ("Irvine", "irvine")]:
    for (cls, src), (r_s, n_s, spring_s) in sorted(shipped[camp].items()):
        # the shipped spring must equal class minus this instrument's offset
        check(f"{camp} class {cls} {src}: spring", spring_s, cls - OFFSET[src])
        got_r, got_n = recompute(pref, cls, src)
        check(f"{camp} class {cls} {src}: r", got_r, r_s)
        check(f"{camp} class {cls} {src}: n", got_n, n_s)

# the classes with no possible census instrument must be absent everywhere
for camp in D["arc"]:
    yrs = {p[0] for p in D["arc"][camp]["census"]}
    for gap in (2001, 2003, 2021, 2022):
        check(f"{camp}: class {gap} absent from census", gap in yrs, False)

# SAT/ACT must be untouched by the re-alignment
b16 = [p for p in D["arc"]["Berkeley"]["sat"] if p[0] == 2016][0]
check("SAT series unmoved by re-alignment (Berkeley 2016)", b16[1], 0.4965)

# --- 3. two-rulers series, from star panel + test panel ---------------------
starp = pd.read_csv(A.star_panel, dtype={"cds14": str}, low_memory=False,
                    usecols=["cds14", "academic_year", "census_primary"])
tp = panel[["cds14", "academic_year", "z_sat_primary"]]
jj = starp.merge(tp, on=["cds14", "academic_year"], how="inner").dropna()
per_year = {int(ay[:4]) + 1: round(stats.pearsonr(dd.census_primary, dd.z_sat_primary)[0], 4)
            for ay, dd in jj.groupby("academic_year") if len(dd) >= 40}
for y, r_ship, n_ship, src in D["rulers"]["census_x_collegebound"]:
    check(f"rulers {y} ({src})", per_year[y], r_ship)
check("rulers pre-2015 mean", round(np.mean(list(per_year.values())), 4),
      D["rulers"]["pre_mean"])

# --- 4. secondary exhibits, from the analysis outputs -----------------------
AN = A.analysis
vb = pd.read_csv(f"{AN}/volume_backcast_by_need_quintile.csv")
piv = vb.pivot_table(index="year", columns="needq", values="apps_per_100_seniors")
ratio = piv["Q1 most advantaged"] / piv["Q5 highest need"]
check("volume Q1/Q5 1999-2005", round(ratio.loc[1999:2005].mean(), 2),
      D["volume"]["ratio_eras"]["1999-2005"])
check("volume Q1/Q5 2021-2025", round(ratio.loc[2021:2025].mean(), 2),
      D["volume"]["ratio_eras"]["2021-2025"])

W = pd.read_csv(f"{AN}/elwr_alltester_wedge_2006_2016.csv")
check("wedge overall mean", round(W.wedge.mean(), 2), D["wedge"]["overall_mean"])
check("wedge share positive", round((W.wedge > 0).mean(), 4), D["wedge"]["share_positive"])
check("wedge n", len(W), D["wedge"]["n"])

J = pd.read_csv(f"{AN}/gpa_sat_drift_2010_2016.csv")
flat = J[J.satz_slope.abs() <= 0.02]
check("flat-SAT n", len(flat), D["gpa_drift"]["flat"]["n"])
check("flat-SAT gpa slope", round(flat.gpa_slope.mean(), 4),
      D["gpa_drift"]["flat"]["mean_gpa_slope"])
check("flat-SAT share rising", round((flat.gpa_slope > 0).mean(), 4),
      D["gpa_drift"]["flat"]["share_rising"])

X = pd.read_csv(f"{AN}/ap_drift_vs_inflation_index.csv").dropna(subset=["I", "d_ap", "dG"])
check("AP drift r(index)", round(stats.pearsonr(X.I, X.d_ap)[0], 4), D["ap_drift"]["r_index"])
rose = X[X.dG > 0]
grew = rose.d_ap > rose.d_ap.median()
check("AP split I (flat half)", round(rose[~grew].I.mean(), 4), D["ap_drift"]["split"]["flat"]["I"])
check("AP split I (grew half)", round(rose[grew].I.mean(), 4), D["ap_drift"]["split"]["grew"]["I"])

# --- 5. AP expansion spot values, independent aggregation -------------------
need = syw.groupby("ceeb").upp_pct.mean().dropna()
qs = pd.qcut(need, 5, labels=["Q1 most advantaged", "Q2", "Q3", "Q4", "Q5 highest need"])
pm = panel[panel.ceeb.notna()].copy(); pm["ceeb"] = pm.ceeb.str.zfill(6)
pm = pm[pm.grade_12_enrollment > 0]
pm["needq"] = pm.ceeb.map(qs)
hs = pm[pm.ap_exams.notna()]
fixed = set(hs[hs.uc_cycle_year.between(1999, 2003)].ceeb) & \
        set(hs[hs.uc_cycle_year.between(2016, 2020)].ceeb) & set(need.index)
check("AP fixed-panel size", len(fixed), D["ap_expansion"]["n_schools"])
for q, y in [("Q1 most advantaged", 2020), ("Q5 highest need", 1999)]:
    dd = pm[(pm.ceeb.isin(fixed)) & (pm.needq == q) & (pm.uc_cycle_year == y) & pm.ap_exams.notna()]
    got = round(100 * dd.ap_exams.sum() / dd.grade_12_enrollment.sum(), 2)
    want = dict((a, b) for a, b in D["ap_expansion"]["series"][q])[y]
    check(f"AP exams/100 {q} {y}", got, want, tol=0.01)

n_ok = sum(PASS)
print(f"\n{n_ok}/{len(PASS)} checks pass")
sys.exit(0 if n_ok == len(PASS) else 1)
