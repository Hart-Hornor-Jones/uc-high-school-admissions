#!/usr/bin/env python3
"""Build history/data_history.js for the long-view page (1999-2025).

Inputs (all read-only):
  - test_context_panel.csv        (AP/SAT/ACT panel, cds14 x academic year)
  - census_achievement_spine.csv  (STAR S9 / CAHSEE / STAR CST / CAASPP spine)
  - school_year_wide.csv          (per-CEEB admit rates & applicants per campus-year)
  - panel/analysis/ precomputed outputs (era arc, backcast, wedge, drift files)

Everything the page shows is precomputed here into one static JS object.
Conventions follow era_arc.py exactly where a published anchor exists:
gate >= 25 applicants to the campus, min 40 schools per correlation,
join on CEEB x admission-cycle year, Pearson r.

Example (run from the repo root, Hart's layout):
  python build\build_history_data.py ^
    --panel "..\..\hs data\ap-sat-act-refined\panel\test_context_panel.csv" ^
    --spine "..\..\hs data\star-scores\panel\census_achievement_spine.csv" ^
    --star-panel "..\..\hs data\star-scores\panel\star_cahsee_panel.csv" ^
    --syw "..\Correlation Matrix 2026-07-05\school_year_wide.csv" ^
    --analysis "..\..\hs data\ap-sat-act-refined\panel\analysis" ^
    --dv "data\dv_admissions_all9.csv" ^
    --out "history\data_history.js"
Then: python build\verify_history_anchors.py (same inputs, plus
--data history\data_history.js) and node build\test_history_page.js history.
"""
import argparse, json, os, sys
import pandas as pd, numpy as np
from scipy import stats

ap = argparse.ArgumentParser()
ap.add_argument("--panel", required=True, help="test_context_panel.csv")
ap.add_argument("--spine", required=True, help="census_achievement_spine.csv")
ap.add_argument("--star-panel", required=True, help="star_cahsee_panel.csv")
ap.add_argument("--syw", required=True, help="school_year_wide.csv")
ap.add_argument("--analysis", required=True, help="panel analysis dir")
ap.add_argument("--dv", required=True, help="dv_admissions_all9.csv (school names)")
ap.add_argument("--out", required=True, help="output data_history.js")
ap.add_argument("--json", default=None, help="optional JSON twin for verification")
A = ap.parse_args()

GATE, MIN_N = 25, 40
CAMPS = {"berk": "Berkeley", "la": "UCLA", "sd": "San Diego", "davis": "Davis",
         "irvine": "Irvine", "sb": "Santa Barbara", "sc": "Santa Cruz",
         "riverside": "Riverside", "merced": "Merced", "uc": "UC systemwide"}
SRC_LABEL = {"star_s9_pac50_reading": "s9",
             "cahsee_ela_pct_passed": "cahsee",
             "star_cst_ela_pct_prof_plus": "cst",
             "caaspp_avg_pct_met": "caaspp"}

# ---------------------------------------------------------------------------
# COHORT ALIGNMENT.  The x-axis is the normative GRADUATING CLASS year, which
# equals the UC admission year: the class of Y applies in fall Y-1 and enters
# in fall Y.  A student in the class of Y sits in grade 9 in spring Y-3,
# grade 10 in spring Y-2, grade 11 in spring Y-1, grade 12 in spring Y.
# Each census instrument therefore carries its own offset from its test spring
# to the class it describes:
#     CAASPP        grade 11, spring S  ->  class S+1
#     STAR CST g11  grade 11, spring S  ->  class S+1
#     CAHSEE        grade 10, spring S  ->  class S+2
#     Stanford 9    grades 9-11 pooled  ->  no single class; centred on S+2
# The college-bound SAT/ACT files run over academic year S-1/S and are
# senior-weighted, so their existing uc_cycle_year (= S) is already the
# class-of-S convention and is left untouched.
COHORT_OFFSET = {"caaspp": 1, "cst11": 1, "cahsee": 2, "s9": 2}
# preference when more than one instrument speaks for the same class
SRC_RANK = {"caaspp": 0, "cst11": 1, "cahsee": 2, "s9": 3}

def r4(x):  return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 4)
def r2(x):  return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), 2)

print("loading inputs ...")
panel = pd.read_csv(A.panel, dtype={"cds14": str, "ceeb": str}, low_memory=False)
spine = pd.read_csv(A.spine, dtype={"cds14": str, "ceeb": str}, low_memory=False)
syw = pd.read_csv(A.syw, dtype={"ceeb": str}, low_memory=False)
syw["ceeb"] = syw.ceeb.str.zfill(6)
AN = A.analysis

import datetime as _dt
out = {"generated": _dt.date.today().isoformat(), "gate": GATE, "min_n": MIN_N}

# ---------------------------------------------------------------- 1. the arc
# College-bound + CAASPP families: as published (era_arc_correlations.csv).
arc_pub = pd.read_csv(os.path.join(AN, "era_arc_correlations.csv"))
arc_pub = arc_pub[arc_pub.gate == GATE]
MEAS = {"SAT (era-bridged z)": "sat", "ACT pct>=21 (z)": "act"}

# Census family, on the graduating-class axis.  Each instrument is taken at
# its own grade from the STAR/CAHSEE panel -- grade 11 for the CST era, so the
# STAR years measure the same construct CAASPP does -- and shifted by its own
# cohort offset.
starp_full = pd.read_csv(A.star_panel, dtype={"cds14": str, "ceeb": str}, low_memory=False,
                         usecols=["ceeb", "uc_cycle_year", "star_ela_g11_pct_prof_plus",
                                  "cahsee_ela_pct_passed_census", "star_s9_read_pac50"])
starp_full = starp_full[starp_full.ceeb.notna()].copy()
starp_full["ceeb"] = starp_full.ceeb.str.zfill(6)

def measure(col, src, spring_lo=None, spring_hi=None):
    """One instrument as (ceeb, spring, class year, value)."""
    d = starp_full[["ceeb", "uc_cycle_year", col]].dropna().rename(
        columns={"uc_cycle_year": "spring", col: "v"})
    if spring_lo is not None: d = d[d.spring >= spring_lo]
    if spring_hi is not None: d = d[d.spring <= spring_hi]
    d = d.copy()
    d["year"] = d.spring + COHORT_OFFSET[src]
    d["source"] = src
    return d[["ceeb", "spring", "year", "v", "source"]]

# CAASPP comes from the counts compilation (the spine's CAASPP rows carry no CEEB)
caaspp = syw[["ceeb", "year", "avg_pct_met"]].dropna().rename(
    columns={"year": "spring", "avg_pct_met": "v"}).copy()
caaspp["year"] = caaspp.spring + COHORT_OFFSET["caaspp"]
caaspp["source"] = "caaspp"

cen = pd.concat([
    measure("star_ela_g11_pct_prof_plus", "cst11"),
    measure("cahsee_ela_pct_passed_census", "cahsee"),
    measure("star_s9_read_pac50", "s9", spring_lo=2000, spring_hi=2000),
    caaspp[["ceeb", "spring", "year", "v", "source"]],
], ignore_index=True)

census_rows = []
for (year, src), t in cen.groupby(["year", "source"]):
    s = syw[syw.year == year]
    if s.empty: continue
    j = s.merge(t[["ceeb", "v"]], on="ceeb", how="left")
    for pref, name in CAMPS.items():
        ar, ap_ = f"{pref}_admit_rate", f"{pref}_applicants"
        if ar not in j.columns: continue
        d = j[j[ap_] >= GATE][[ar, "v"]].dropna()
        if len(d) >= MIN_N:
            census_rows.append(dict(campus=name, year=int(year), source=src,
                                    spring=int(t.spring.iloc[0]),
                                    r=stats.pearsonr(d[ar], d["v"])[0], n=len(d)))
census = pd.DataFrame(census_rows)
census["rank"] = census.source.map(SRC_RANK)

arc = {}
for name in CAMPS.values():
    e = {}
    for meas, key in MEAS.items():
        dd = arc_pub[(arc_pub.campus == name) & (arc_pub.measure == meas)].sort_values("year")
        e[key] = [[int(y), r4(r), int(n)] for y, r, n in zip(dd.year, dd.r, dd.n)]
    dd = census[census.campus == name].sort_values("year") if len(census) else pd.DataFrame()
    e["census"] = ([[int(y), r4(r), int(n), s, int(sp_)] for y, r, n, s, sp_ in
                    zip(dd.year, dd.r, dd.n, dd.source, dd.spring)] if len(dd) else [])
    arc[name] = e
out["arc"] = arc

# honest per-campus summary, computed not asserted: post-blind mean on the
# census ruler (CAASPP 2022-25) and last positive college-bound year.
groups = {}
for name in CAMPS.values():
    ca = census[(census.campus == name) & (census.source == "caaspp")
                & (census.year >= 2023)] if len(census) else pd.DataFrame(columns=["r"])
    sat = arc_pub[(arc_pub.campus == name) & (arc_pub.measure == "SAT (era-bridged z)")]
    pos = sat[sat.r > 0]
    groups[name] = {"post_blind_mean": r4(ca.r.mean() if len(ca) else None),
                    "sat_last_positive": int(pos.year.max()) if len(pos) else None,
                    "sat_peak": r4(sat.r.max() if len(sat) else None),
                    "sat_peak_year": int(sat.loc[sat.r.idxmax()].year) if len(sat) else None}
out["campus_summary"] = groups

# how well two census instruments describing the SAME class agree
_ag = []
for (nm, yy), g in census.groupby(["campus", "year"]):
    if len(g) > 1:
        vv = g.sort_values("rank").r.tolist()
        _ag.append(abs(vv[0] - vv[1]))
out["census_agreement"] = {"pairs": len(_ag),
                           "mean_abs_diff": r4(np.mean(_ag)) if _ag else None,
                           "median_abs_diff": r4(np.median(_ag)) if _ag else None}

out["alignment"] = {
    "axis": "graduating class year (= UC admission year)",
    "rows": [
        ["caaspp", "CAASPP", "11", 1, "spring S describes the class of S+1"],
        ["cst11",  "STAR CST", "11", 1, "spring S describes the class of S+1"],
        ["cahsee", "CAHSEE", "10", 2, "spring S describes the class of S+2"],
        ["s9",     "Stanford 9", "9-11 pooled", 2, "no single class; centered on S+2"],
        ["sat",    "SAT / ACT", "12 (senior-weighted)", 0, "academic year S-1/S describes the class of S"],
    ]}

# ------------------------------------------------------- 2. two rulers chart
# (a) census x college-bound per academic year — the validation battery's own
# convention (section F): star_cahsee_panel census_primary x panel z_sat_primary,
# FULL overlap at cds14 grain (not CEEB-gated), per academic year.
starp = pd.read_csv(A.star_panel, dtype={"cds14": str, "ceeb": str},
                    usecols=["cds14", "academic_year", "census_primary",
                             "census_primary_source"], low_memory=False)
tp = panel[["cds14", "academic_year", "z_sat_primary"]]
jj = starp.merge(tp, on=["cds14", "academic_year"], how="inner")
rul_pre = []
for ay, dd in jj.groupby("academic_year"):
    d = dd[["census_primary", "z_sat_primary"]].dropna()
    if len(d) >= MIN_N:
        src = dd.dropna(subset=["census_primary", "z_sat_primary"]) \
                .census_primary_source.mode().iloc[0]
        rul_pre.append([int(ay[:4]) + 1,
                        r4(stats.pearsonr(d.census_primary, d.z_sat_primary)[0]),
                        int(len(d)), SRC_LABEL[src]])
# (b) SAT x CAASPP in the overlap (the 2026-07-30 ruler diagnostic), cycles 2016-2020
tp2 = panel[panel.ceeb.notna()][["ceeb", "uc_cycle_year", "z_sat_primary"]].copy()
tp2["ceeb"] = tp2.ceeb.str.zfill(6)
rul_ov = []
for year in range(2015, 2021):
    s = syw[syw.year == year][["ceeb", "avg_pct_met"]]
    t = tp2[tp2.uc_cycle_year == year]
    d = s.merge(t, on="ceeb").dropna(subset=["avg_pct_met", "z_sat_primary"])
    if len(d) >= MIN_N:
        rul_ov.append([int(year), r4(stats.pearsonr(d.avg_pct_met, d.z_sat_primary)[0]), int(len(d))])
pre_vals = [x[1] for x in rul_pre]
out["rulers"] = {"census_x_collegebound": rul_pre, "sat_x_caaspp": rul_ov,
                 "pre_mean": r4(np.mean(pre_vals)),
                 "cst_mean": r4(np.mean([x[1] for x in rul_pre if x[3] == "cst"]))}

# ------------------------------------------------------- 3. volume backcast
vb = pd.read_csv(os.path.join(AN, "volume_backcast_by_need_quintile.csv"))
vol = {}
for q, dd in vb.groupby("needq"):
    dd = dd.sort_values("year")
    vol[q] = [[int(y), r2(v)] for y, v in zip(dd.year, dd.apps_per_100_seniors)]
piv = vb.pivot_table(index="year", columns="needq", values="apps_per_100_seniors")
q1, q5 = piv["Q1 most advantaged"], piv["Q5 highest need"]
ratio = (q1 / q5)
out["volume"] = {"series": vol,
                 "ratio_eras": {"1999-2005": r2(ratio.loc[1999:2005].mean()),
                                "2006-2012": r2(ratio.loc[2006:2012].mean()),
                                "2013-2019": r2(ratio.loc[2013:2019].mean()),
                                "2021-2025": r2(ratio.loc[2021:2025].mean())}}

# ------------------------------------------------- 4. AP expansion by quintile
# fixed-need quintiles: identical rule to the volume backcast (mean UPP, qcut 5)
need = syw.groupby("ceeb").upp_pct.mean().rename("upp_fixed").reset_index().dropna()
need["needq"] = pd.qcut(need.upp_fixed, 5,
                        labels=["Q1 most advantaged", "Q2", "Q3", "Q4", "Q5 highest need"])
pm = panel[panel.ceeb.notna()].copy()
pm["ceeb"] = pm.ceeb.str.zfill(6)
apx = pm[["ceeb", "uc_cycle_year", "ap_exams", "ap_exams_ge_3", "grade_12_enrollment"]].rename(
    columns={"uc_cycle_year": "year"})
apx = apx.merge(need[["ceeb", "needq"]], on="ceeb", how="inner")
apx = apx[(apx.grade_12_enrollment > 0)]
# fixed panel: AP data observed both early (cycles 1999-2003) and late (2016-2020)
has_ap = apx[apx.ap_exams.notna()]
early = set(has_ap[has_ap.year.between(1999, 2003)].ceeb)
late = set(has_ap[has_ap.year.between(2016, 2020)].ceeb)
fixedp = early & late
apf = apx[apx.ceeb.isin(fixedp) & apx.ap_exams.notna()]
ap_series = {}
for q, dd in apf.groupby("needq", observed=True):
    g = dd.groupby("year").apply(
        lambda x: 100 * x.ap_exams.sum() / x.grade_12_enrollment.sum(), include_groups=False)
    ap_series[str(q)] = [[int(y), r2(v)] for y, v in g.items() if 1999 <= y <= 2020]
# pass share (exams scored 3+) on the same fixed panel, per quintile
ps = apf.dropna(subset=["ap_exams_ge_3"])
pass_series = {}
for q, dd in ps.groupby("needq", observed=True):
    g = dd.groupby("year").apply(
        lambda x: 100 * x.ap_exams_ge_3.sum() / x.ap_exams.sum(), include_groups=False)
    pass_series[str(q)] = [[int(y), r2(v)] for y, v in g.items() if 1999 <= y <= 2020]
out["ap_expansion"] = {"series": ap_series, "n_schools": len(fixedp),
                       "pass_share": pass_series}

# school-name lookup for scatter tooltips (last observed name per CEEB)
dv = pd.read_csv(A.dv, dtype={"ceeb": str}, usecols=["ceeb", "year", "school_name"])
dv["ceeb"] = dv.ceeb.str.zfill(6)
names = dv.sort_values("year").groupby("ceeb").school_name.last()
def nice(s):
    s = str(s).title()
    for a, b in [("'S", "'s"), (" Of ", " of "), (" And ", " and "), (" The ", " the ")]:
        s = s.replace(a, b)
    return s

# ------------------------------------------------- 5. AP drift vs inflation
X = pd.read_csv(os.path.join(AN, "ap_drift_vs_inflation_index.csv"), dtype={"ceeb": str})
X["ceeb"] = X.ceeb.str.zfill(6)
X = X.dropna(subset=["I", "d_ap", "dG"])
r_I = stats.pearsonr(X.I, X.d_ap)[0]
r_dG = stats.pearsonr(X.dG, X.d_ap)[0]
rose = X[X.dG > 0].copy()
rose["ap_grew"] = rose.d_ap > rose.d_ap.median()
split = rose.groupby("ap_grew")[["dG", "I", "d_ap"]].mean()
out["ap_drift"] = {
    "points": [[r4(a), r4(b), nice(nm)] for a, b, nm in
               zip(X.d_ap, X.I, X.ceeb.map(names).fillna(X.name))],
    "n": int(len(X)), "r_index": r4(r_I), "r_dG": r4(r_dG),
    "split": {"flat": {"I": r4(split.loc[False, "I"]), "dG": r4(split.loc[False, "dG"]),
                       "d_ap": r4(split.loc[False, "d_ap"]), "n": int((~rose.ap_grew).sum())},
              "grew": {"I": r4(split.loc[True, "I"]), "dG": r4(split.loc[True, "dG"]),
                       "d_ap": r4(split.loc[True, "d_ap"]), "n": int(rose.ap_grew.sum())}}}

# ------------------------------------------------------------- 6. the wedge
W = pd.read_csv(os.path.join(AN, "elwr_alltester_wedge_2006_2016.csv"))
wy = []
for y, dd in W.groupby("uc_cycle_year"):
    wy.append([int(y), r2(dd.wedge.mean()), r2(dd.wedge.quantile(.25)),
               r2(dd.wedge.quantile(.75)), int(len(dd))])
W["ceeb"] = W.ceeb.astype(str).str.zfill(6)
wm = W.groupby("ceeb").wedge.mean()
cm = syw[syw.year.between(2015, 2019)].groupby("ceeb").avg_pct_met.mean()
wj = pd.concat([wm, cm], axis=1).dropna()
out["wedge"] = {"yearly": wy, "overall_mean": r2(W.wedge.mean()),
                "share_positive": r4((W.wedge > 0).mean()), "n": int(len(W)),
                "r_school_achievement": r4(stats.pearsonr(wj.wedge, wj.avg_pct_met)[0]),
                "r_school_achievement_n": int(len(wj))}

# ------------------------------------------------------------ 7. GPA drift
J = pd.read_csv(os.path.join(AN, "gpa_sat_drift_2010_2016.csv"))
J["ceeb6"] = J.ceeb.astype(int).astype(str).str.zfill(6)
flat = J[J.satz_slope.abs() <= 0.02]
out["gpa_drift"] = {
    "points": [[r4(a), r4(b), nice(nm)] for a, b, nm in
               zip(J.satz_slope, J.gpa_slope, J.ceeb6.map(names).fillna("—"))],
    "n": int(len(J)),
    "mean_gpa_slope": r4(J.gpa_slope.mean()),
    "share_rising": r4((J.gpa_slope > 0).mean()),
    "r_slopes": r4(stats.pearsonr(J.gpa_slope, J.satz_slope)[0]),
    "flat": {"n": int(len(flat)), "mean_gpa_slope": r4(flat.gpa_slope.mean()),
             "share_rising": r4((flat.gpa_slope > 0).mean())}}

# ------------------------------------------------------------- 8. anchors
b16 = arc_pub[(arc_pub.campus == "Berkeley") & (arc_pub.year == 2016)
              & (arc_pub.measure == "SAT (era-bridged z)")]
out["anchors"] = {
    "berkeley_2016_sat_r": r4(b16.r.iloc[0]), "berkeley_2016_sat_n": int(b16.n.iloc[0]),
    "rulers_pre_mean": out["rulers"]["pre_mean"],
    "wedge_overall_mean": out["wedge"]["overall_mean"],
    "volume_ratio_1999_2005": out["volume"]["ratio_eras"]["1999-2005"],
    "flat_sat_gpa_slope": out["gpa_drift"]["flat"]["mean_gpa_slope"],
    "ap_drift_r": out["ap_drift"]["r_index"]}

# ------------------------------------------------------------------ write
js = "window.HISTORY_DATA = " + json.dumps(out, separators=(",", ":")) + ";\n"
with open(A.out, "w", encoding="utf-8") as f:
    f.write("// generated by build/build_history_data.py — do not edit by hand\n")
    f.write(js)
if A.json:
    with open(A.json, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
print(f"wrote {A.out} ({os.path.getsize(A.out):,} bytes)")
print("anchors:", json.dumps(out["anchors"]))
print("census arc points:", sum(len(v["census"]) for v in arc.values()))
print("rulers pre:", out["rulers"]["census_x_collegebound"])
print("rulers overlap:", out["rulers"]["sat_x_caaspp"])
print("campus summary:", json.dumps(groups))
