#!/usr/bin/env python3
"""
make_site_data.py  -  build the data layer for the interactive site (per-year structure).

Reads data/panel_all9_by_year.csv (built by build_panel_all9.py) and the ELWR/AWPE file,
and writes:
  - data.js                      (window.UCDATA = {...}; loaded by index.html at repo root)
  - data/cross_section_all9.csv  (tidy unified file for the DEFAULT pooled period)

data.js stores a per-(campus,school) panel of raw yearly counts + covariates; the site pools
across the selected year/period and computes every rate client-side (ratio-of-sums over
jointly-observed years), so years/periods are explorable just like campuses.

Run:  python3 scripts/make_site_data.py
"""
import csv, json, os, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
START = 2015   # first admission year kept in the site panel (covariate era)

CAMPUSES = ["Berkeley","Davis","Irvine","Los Angeles","Merced",
            "Riverside","San Diego","Santa Barbara","Santa Cruz"]
CIDX = {c: i for i, c in enumerate(CAMPUSES)}

def fnum(x):
    x = (x or "").strip()
    if x in ("", "*", "NA", "NaN", "nan"): return None
    try: return float(x)
    except ValueError: return None
def inum(x):
    v = fnum(x); return None if v is None else int(round(v))
def r1(x): return None if x is None else round(x, 1)
def g2(x): x = fnum(x); return None if x is None else round(x, 2)   # GPA: parse + 2 decimals
def ceeb6(x):
    x = str(x or "").strip(); return x.zfill(6) if x.isdigit() else x

# ---- ELWR/AWPE writing requirement + SAT/ACT enrollee averages (latest year per CEEB) ----
# pct_enrolled_met_requirement = % of ENROLLED students who satisfied the UC Entry Level Writing
# Requirement AT ENTRY -- via the AWPE exam OR other qualifying methods (AP/IB/SAT/ACT/transferable
# course) -- i.e. who did NOT need first-year remedial writing coursework. (It is NOT "ever met".)
# SAT/ACT are ENROLLEE averages, reported only for older years (~2006-2020, none after 2020). They are
# kept latest-year-per-CEEB for the school profile ONLY (self-selected enrollees, small N, pre-test-blind);
# they are deliberately never offered as an axis. Both dicts track their own latest observed year.
awpe = {}
tests = {}   # ceeb -> [avg_sat_reading, avg_sat_writing, avg_act_writing, year]
elwr = os.path.join(DATA, "elwr_school_year_wide.csv")
if os.path.exists(elwr):
    for r in csv.DictReader(open(elwr, encoding="utf-8", errors="replace")):
        ce = ceeb6(r.get("school_code")); yr = inum(r.get("academic_year"))
        if not ce or yr is None: continue
        wm = fnum(r.get("pct_enrolled_met_requirement"))
        if wm is not None and (ce not in awpe or yr > awpe[ce][1]): awpe[ce] = [round(wm, 1), yr]
        sr = fnum(r.get("avg_sat_reading")); sw = fnum(r.get("avg_sat_writing")); aw = fnum(r.get("avg_act_writing"))
        if (sr is not None or sw is not None or aw is not None) and (ce not in tests or yr > tests[ce][3]):
            tests[ce] = [r1(sr), r1(sw), r1(aw), yr]

# ---- cleaned A-G denominators (data-quality fix; see Data Cleaning 2026-06-07 report) ----
# Per (cds14, spring year) the build substitutes a cleaned A-G eligible count, splitting it into
#   Gc (completion axis): impute HIGH-confidence isolated collapses; suppress collapse/chronic-zero;
#                         keep tiny (<10) and moderate-drop at raw (a small real count is a real rate)
#   Gp (per-eligible rates): impute HIGH-confidence collapses; suppress collapse/chronic/tiny;
#                         keep moderate-drop at raw (left untouched per review hold)
AGCLEAN = {}
_agc = os.path.join(DATA, "ag_eligibility_cleaned.csv")
if os.path.exists(_agc):
    for r in csv.DictReader(open(_agc, encoding="utf-8")):
        AGCLEAN[(r["cds14"], int(r["year"]))] = (r["recommended_action"], r["impute_confidence"],
                                                 inum(r["ag_met_clean"]), inum(r["ag_met_raw"]))
def clean_G(cds, yr, raw_G):
    rec = AGCLEAN.get((cds, yr))
    if not rec: return raw_G, raw_G
    action, conf, met_clean, _ = rec
    if action == "SUPPRESS_RATE":
        if conf == "HIGH" and met_clean is not None: return met_clean, met_clean
        return None, None
    if action == "FLOOR": return raw_G, None
    return raw_G, raw_G

# ---- UC freshman graduation rates by source high school (UC Info Center dashboard) ----
# data/grad_rates_by_hs.csv (built by build/parse_grad_rates.py): per (campus, ceeb, entry year),
# the school's UC freshman entrants that fall (cohort_n, shown only when >=10) and their
# 1st-year retention / 4-, 5-, 6-year graduation rates (integer percents).
# "All" rows pool all UC campuses (the well-covered series); campus rows are big feeders only.
# Maturity: 6-yr rates exist through entry 2019, 5-yr 2020, 4-yr 2021, retention 2024.
grad  = defaultdict(list)   # ceeb        -> [[entry_year, N, ret1, g4, g5, g6], ...]
gradC = defaultdict(list)   # "ci|ceeb"   -> same rows, entrants to that campus only
_gr = os.path.join(DATA, "grad_rates_by_hs.csv")
if os.path.exists(_gr):
    for r in csv.DictReader(open(_gr, encoding="utf-8")):
        row = [inum(r["entry_year"]), inum(r["cohort_n"]), inum(r["ret1_pct"]),
               inum(r["grad4_pct"]), inum(r["grad5_pct"]), inum(r["grad6_pct"])]
        ce = ceeb6(r["ceeb"])
        if r["campus"] == "All": grad[ce].append(row)
        elif r["campus"] in CIDX: gradC[f"{CIDX[r['campus']]}|{ce}"].append(row)
    for k in grad: grad[k].sort()
    for k in gradC: gradC[k].sort()

# ---- panel: (campusIdx|ceeb) -> [[year,A,D,E,C,Gc,H,ela,math,upp,Gp,agpa,dgpa,egpa], ...] ----
panel = defaultdict(list)
meta = {}              # ceeb -> [name, city, county, cds] (latest year wins)
meta_year = {}
for r in csv.DictReader(open(os.path.join(DATA, "panel_all9_by_year.csv"), encoding="utf-8")):
    camp = r["campus"]
    if camp not in CIDX: continue
    yr = inum(r["year"])
    if yr is None or yr < START: continue
    ce = ceeb6(r["ceeb"])
    A = inum(r["applicants"]); D = inum(r["admits"]); E = inum(r["enrollees"])
    C = inum(r["ag_cohort"]); G = inum(r["ag_met_uccsu_count"]); H = inum(r["enroll_9_12"])
    ela = r1(fnum(r["ela_pct_met"])); math = r1(fnum(r["math_pct_met"])); upp = r1(fnum(r["upp_pct"]))
    agpa = g2(r.get("app_gpa")); dgpa = g2(r.get("adm_gpa")); egpa = g2(r.get("enr_gpa"))
    # skip totally empty rows (no funnel and no covariate)
    if A is None and D is None and E is None and ela is None and upp is None and G is None:
        continue
    Gc, Gp = clean_G(r["cds14"], yr, G)   # A-G eligible: cleaned for completion (Gc) and per-eligible rates (Gp)
    panel[f"{CIDX[camp]}|{ce}"].append([yr, A, D, E, C, Gc, H, ela, math, upp, Gp, agpa, dgpa, egpa])
    if ce not in meta_year or yr >= meta_year[ce]:
        meta[ce] = [r["school_name"], r["city"], r["county"], r["cds14"]]; meta_year[ce] = yr
for k in panel: panel[k].sort()

# ---- metric metadata (X-axis merit/context + selectable outcome rates) ----
# num/den letters map to panel array indices in index.html: A=1 D=2 E=3 C=4 G=5 H=6
METRICS = [
  # merit / context (typical X-axis)
  {"key":"avg",  "label":"CAASPP proficiency — avg % met (gr 11)", "short":"CAASPP avg % met", "role":"merit",   "fmt":"pct"},
  {"key":"ela",  "label":"CAASPP ELA — % met (gr 11)",  "short":"CAASPP ELA % met",  "role":"merit",   "fmt":"pct"},
  {"key":"math", "label":"CAASPP Math — % met (gr 11)", "short":"CAASPP Math % met", "role":"merit",   "fmt":"pct"},
  {"key":"ag",   "label":"A–G completion — % of cohort UC/CSU-eligible", "short":"A–G completion", "role":"merit", "fmt":"pct", "num":"G", "den":"C"},
  {"key":"upp",  "label":"Poverty / high-need — UPP %", "short":"UPP (poverty)", "role":"context", "fmt":"pct"},
  {"key":"awpe", "label":"Writing req. met — ELWR/AWPE (enrollees)", "short":"ELWR/AWPE", "role":"context", "fmt":"pct",
                 "caveat":"UC enrollees only (self-selected, small N); latest year available per school."},
  {"key":"app_gpa","label":"Applicant GPA — UC weighted-capped (gr 10–11)","short":"Applicant GPA","role":"merit","fmt":"gpa",
                 "caveat":"Mean UC-recalculated GPA of the school's UC freshman APPLICANTS (weighted, honors-capped). An applicant-pool merit measure — distinct from CAASPP, which covers all grade-11 students."},
  {"key":"adm_gpa","label":"Admit GPA — UC weighted-capped (admitted students)","short":"Admit GPA","role":"merit","fmt":"gpa",
                 "caveat":"Mean GPA of ADMITTED students. Partly downstream of the admit decision (a more selective campus shows a higher bar), so read it as the GPA level UC accepted at the school, not a pure measure of school strength."},
  {"key":"grad6_prior","label":"UC-wide 6-yr graduation — earlier entrants, any campus (cohorts 6–10 yrs before period)","short":"UC-wide 6-yr grad (prior cohorts)","role":"merit","fmt":"pct","grad":{"col":"g6","win":"prior"},
                 "caveat":"N-weighted 6-yr UC graduation rate of the school's earlier UC entrants (entry cohorts 6-10 years before the selected period starts) - the most recent rates fully observable, and knowable to admissions readers, by decision time. All-UC-campus rates; cohorts shown only when >=10 entrants."},
  # outcome rates (selectable Y-axis); computed period-consistently as ratio-of-sums
  {"key":"ret1_same","label":"UC-wide 1st-year retention — this period's entrants, any campus","short":"UC-wide 1st-yr retention","role":"merit","fmt":"pct","grad":{"col":"r1","win":"same"},
                 "caveat":"Share of the school's UC freshman entrants in the selected period still enrolled after one year (available through entry 2024). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"grad4_same","label":"UC-wide 4-yr graduation — this period's entrants, any campus","short":"UC-wide 4-yr grad","role":"merit","fmt":"pct","grad":{"col":"g4","win":"same"},
                 "caveat":"4-year UC graduation rate of entrants in the selected period; mature only through entry 2021 (empty for recent periods - try 2016-2019). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"grad6_same","label":"UC-wide 6-yr graduation — this period's entrants, any campus","short":"UC-wide 6-yr grad","role":"merit","fmt":"pct","grad":{"col":"g6","win":"same"},
                 "caveat":"6-year UC graduation rate of entrants in the selected period; mature only through entry 2019 (empty for recent periods - try 2016-2019). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"ret1_camp","label":"1st-year retention at this campus — this period's entrants","short":"Retention (this campus)","role":"outcome","fmt":"pct","grad":{"col":"r1","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Retention is available through entry 2024."},
  {"key":"grad4_camp","label":"4-yr graduation at this campus — this period's entrants","short":"4-yr grad (this campus)","role":"outcome","fmt":"pct","grad":{"col":"g4","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Mature only through entry 2021 (empty for recent periods - try 2016-2019)."},
  {"key":"grad6_camp","label":"6-yr graduation at this campus — this period's entrants","short":"6-yr grad (this campus)","role":"outcome","fmt":"pct","grad":{"col":"g6","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Mature only through entry 2019 (empty for recent periods - try 2016-2019)."},
  {"key":"admit_rate","label":"Admit rate to this campus (admits ÷ applicants)",        "short":"Admit rate",        "role":"outcome","fmt":"ratio","num":"D","den":"A"},
  {"key":"yield",     "label":"Enrollment yield (enrollees ÷ admits)",      "short":"Yield (enroll÷adm)","role":"outcome","fmt":"ratio","num":"E","den":"D"},
  {"key":"app_rate",  "label":"Application rate (applicants ÷ A–G eligible)","short":"Application rate",  "role":"outcome","fmt":"ratio","num":"A","den":"Gp"},
  {"key":"adm_per_elig","label":"Admits ÷ A–G eligible",                    "short":"Admits ÷ eligible", "role":"outcome","fmt":"ratio","num":"D","den":"Gp"},
  {"key":"enr_per_elig","label":"Enrollees ÷ A–G eligible",                 "short":"Enroll ÷ eligible", "role":"outcome","fmt":"ratio","num":"E","den":"Gp"},
  {"key":"app_per_head","label":"Applicants ÷ grade 9–12 enrollment",       "short":"Apps ÷ enrollment", "role":"outcome","fmt":"ratio","num":"A","den":"H"},
  {"key":"adm_per_head","label":"Admits ÷ grade 9–12 enrollment",           "short":"Admits ÷ enrollment","role":"outcome","fmt":"ratio","num":"D","den":"H"},
  {"key":"enr_per_head","label":"Enrollees ÷ grade 9–12 enrollment",        "short":"Enroll ÷ enrollment","role":"outcome","fmt":"ratio","num":"E","den":"H"},
]

# ---- periods (presets + single years) ----
PERIODS = [
  {"key":"p2325","label":"2023–2025 (recent, test-blind)","years":[2023,2024,2025]},
  {"key":"p1619","label":"2016–2019 (pre-test-blind)","years":[2016,2017,2018,2019]},
] + [{"key":f"y{y}","label":str(y),"years":[y]} for y in (2025,2024,2023,2022,2021,2020,2019,2018,2017,2016)]
DEFAULT_PERIOD = "p2325"

UCDATA = {
  "generated": datetime.date.today().isoformat(),
  "startYear": START,
  "campuses": CAMPUSES,
  "meta": meta,
  "awpe": awpe,
  "tests": tests,
  "panel": panel,
  "grad": grad,
  "gradC": gradC,
  "metrics": METRICS,
  "periods": PERIODS,
  "defaultPeriod": DEFAULT_PERIOD,
}
with open(os.path.join(REPO, "data.js"), "w", encoding="utf-8") as fh:
    fh.write("/* Auto-generated by scripts/make_site_data.py — do not edit by hand. */\n")
    fh.write("window.UCDATA = ")
    json.dump(UCDATA, fh, separators=(",", ":"), ensure_ascii=False)
    fh.write(";\n")

# ---- tidy unified CSV for the DEFAULT pooled period ----
IDX = {"A":1,"D":2,"E":3,"C":4,"G":5,"H":6,"Gp":10}
def jsum(rows, num, den):
    sn = sd = 0.0; ok = False
    for row in rows:
        a = row[IDX[num]]; b = row[IDX[den]]
        if a is not None and b is not None: sn += a; sd += b; ok = True
    return (sn, sd) if (ok and sd > 0) else (None, None)
def meanof(rows, idx):
    vals = [row[idx] for row in rows if row[idx] is not None]
    return sum(vals)/len(vals) if vals else None

def rate(rows, num, den, pct):
    sn, sd = jsum(rows, num, den)
    if sn is None: return None
    return round(100*sn/sd, 2) if pct else round(sn/sd, 4)

GRIX = {"r1":2,"g4":3,"g5":4,"g6":5}
def grad_pool(ce, col, years):
    """N-weighted pooled grad/retention percent over the given entry years (All-UC rows)."""
    sv = sw = 0
    for row in grad.get(ce, []):
        if row[0] in years and row[GRIX[col]] is not None and row[1]:
            sv += row[GRIX[col]] * row[1]; sw += row[1]
    return (round(sv / sw, 1), sw) if sw else (None, None)

dp = next(p for p in PERIODS if p["key"] == DEFAULT_PERIOD)["years"]
cols = ["campus","ceeb","cds14","school_name","city","county","applicants","admits","enrollees",
        "admit_rate","yield","application_rate","admits_per_eligible","enr_per_eligible",
        "apps_per_enrollment","admits_per_enrollment","enr_per_enrollment",
        "caaspp_ela_pct_met","caaspp_math_pct_met","caaspp_avg_pct_met","ag_completion_pct",
        "upp_pct","lcff_plus","awpe_writing_met_pct","awpe_year","applicant_gpa","admit_gpa",
        "uc_grad6_prior_pct","uc_grad6_prior_n","uc_ret1_same_pct","uc_ret1_same_n"]
out = []
for key, allrows in panel.items():
    ci, ce = key.split("|"); ci = int(ci)
    rows = [r for r in allrows if r[0] in dp]
    if not rows: continue
    sumA = sum(r[1] for r in rows if r[1] is not None)
    sumD = sum(r[2] for r in rows if r[2] is not None)
    sumE = sum(r[3] for r in rows if r[3] is not None)
    ela = meanof(rows, 7); math = meanof(rows, 8); upp = meanof(rows, 9)
    avg = round((ela+math)/2, 2) if (ela is not None and math is not None) else (round(ela,2) if ela is not None else (round(math,2) if math is not None else None))
    snG, sdC = jsum(rows, "G", "C"); agpct = round(100*snG/sdC,2) if snG is not None else None
    nm, city, cty, cds = meta.get(ce, ["","","",""])
    aw = awpe.get(ce, [None, None])
    agpa_m = meanof(rows, 11); dgpa_m = meanof(rows, 12)
    out.append([CAMPUSES[ci], ce, cds, nm, city, cty, sumA, sumD, sumE,
        rate(rows,"D","A",True), rate(rows,"E","D",True), rate(rows,"A","Gp",False),
        rate(rows,"D","Gp",False), rate(rows,"E","Gp",False), rate(rows,"A","H",False),
        rate(rows,"D","H",False), rate(rows,"E","H",False),
        round(ela,1) if ela is not None else None, round(math,1) if math is not None else None, avg, agpct,
        round(upp,1) if upp is not None else None,
        "Y" if (upp is not None and upp >= 75) else "N", aw[0], aw[1],
        round(agpa_m,2) if agpa_m is not None else None, round(dgpa_m,2) if dgpa_m is not None else None,
        *grad_pool(ce, "g6", set(range(min(dp)-10, min(dp)-5))), *grad_pool(ce, "r1", set(dp))])
out.sort(key=lambda r: (r[0], -(r[6] or 0)))
with open(os.path.join(DATA, "cross_section_all9.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(cols); w.writerows(out)

# ---- report ----
size = os.path.getsize(os.path.join(REPO, "data.js"))
print(f"panel keys (campus×school): {len(panel)}")
print(f"school meta (unique CEEB)  : {len(meta)}")
print(f"AWPE schools               : {len(awpe)}")
print(f"grad-rate schools (All-UC) : {len(grad)} | campus-specific keys: {len(gradC)}")
print(f"data.js                    : {size/1024/1024:.2f} MB")
print(f"cross_section_all9 rows     : {len(out)} (default period {dp})")
yrs = sorted({row[0] for rows in panel.values() for row in rows})
print(f"years in panel             : {yrs}")
