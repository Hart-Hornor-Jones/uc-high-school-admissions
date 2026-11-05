#!/usr/bin/env python3
"""
make_site_data.py  -  build the data layer for the interactive site (per-year structure).

Reads data/panel_all9_by_year.csv (built by build_panel_all9.py) and the ELWR/AWPE file,
and writes:
  - data.js                      (window.UCDATA = {...}; loaded by index.html at repo root)
  - data_parts/*.js              (school covariates, one funnel part per campus, UC outcomes;
                                  fetched on demand by ucparts.js - see the write section)
  - data/cross_section_all9.csv  (tidy unified file for the DEFAULT pooled period)

data.js stores a per-(campus,school) panel of raw yearly counts + covariates; the site pools
across the selected year/period and computes every rate client-side (ratio-of-sums over
jointly-observed years), so years/periods are explorable just like campuses.

Denominators carried per school-year: applicants (UC), graduates (CDE diploma graduates, classes
of 2017+), A-G completers (CDE, cleaned) and grade 9-12 enrollment (CALPADS). School coordinates
(CDE directory) ride along in `meta` so the site can compute each school's distance to a campus.

Run:  python3 scripts/make_site_data.py [--generated YYYY-MM-DD]
"""
import csv, json, os, sys, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")
START = 2015   # first admission year kept in the site panel (covariate era)
# `generated` is the build date printed in the page footer. It defaults to today; pass
# --generated YYYY-MM-DD to keep an earlier date when only the file layout is rebuilt.
GENERATED = sys.argv[sys.argv.index("--generated") + 1] if "--generated" in sys.argv else datetime.date.today().isoformat()

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

# ---- graduates: the per-graduate denominator (CDE four-year cohort x regular-diploma rate) ----
# ag_eligibility_cleaned.csv carries, per (cds14, class year), the ACGR cohort and the school's
# regular-high-school-diploma rate. graduates = round(cohort * diploma_rate / 100). The same CALPADS
# reporting failure that zeroes A-G counts also zeroes a school's diploma rate in isolated years
# (e.g. a 97% school reporting 0.7% for one class), so a year is SUPPRESSED (None) when its diploma
# rate is below 60% of the school's median over its other years, or when it leaves fewer than 10
# graduates (the same floor the per-eligible rates use). A school's genuine, stable low rate is kept.
DIPL = defaultdict(dict)   # cds14 -> {year: (cohort, diploma_rate)}
if os.path.exists(_agc):
    for r in csv.DictReader(open(_agc, encoding="utf-8")):
        c = fnum(r.get("cohort")); d = fnum(r.get("diploma_rate"))
        if c is not None and d is not None: DIPL[r["cds14"]][int(r["year"])] = (c, d)
def graduates(cds, yr):
    rec = DIPL.get(cds, {}).get(yr)
    if not rec: return None
    c, d = rec
    others = sorted(v[1] for y, v in DIPL[cds].items() if y != yr)
    if others:
        med = others[len(others)//2] if len(others) % 2 else (others[len(others)//2-1] + others[len(others)//2]) / 2
        if med > 0 and d < 0.6 * med: return None      # isolated collapse (reporting failure), not a real class
    g = int(round(c * d / 100))
    return g if g >= 10 else None

# ---- school coordinates (CDE directory, via build/build_school_locations.py) ----
LOC = {}
_loc = os.path.join(DATA, "components", "school_locations.csv")
if os.path.exists(_loc):
    for r in csv.DictReader(open(_loc, encoding="utf-8")):
        la = fnum(r.get("latitude")); lo = fnum(r.get("longitude"))
        if la is not None and lo is not None: LOC[r["cds14"].zfill(14)] = (la, lo)
# main-campus coordinates (used client-side for straight-line distance school -> campus)
CAMPUS_LL = {"Berkeley":[37.8719,-122.2585],"Davis":[38.5382,-121.7617],"Irvine":[33.6405,-117.8443],
             "Los Angeles":[34.0689,-118.4452],"Merced":[37.3661,-120.4227],"Riverside":[33.9737,-117.3281],
             "San Diego":[32.8801,-117.2340],"Santa Barbara":[34.4140,-119.8489],"Santa Cruz":[36.9916,-122.0583]}

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

# ---- panel: (campusIdx|ceeb) -> [[year,A,D,E,C,Gc,H,ela,math,upp,Gp,agpa,dgpa,egpa,Gr], ...] ----
panel = defaultdict(list)
meta = {}              # ceeb -> [name, city, county, cds, lat, lon] (latest year wins; lat/lon null if unlocated)
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
    Gr = graduates(r["cds14"], yr)        # diploma graduates of the class (per-graduate denominator)
    panel[f"{CIDX[camp]}|{ce}"].append([yr, A, D, E, C, Gc, H, ela, math, upp, Gp, agpa, dgpa, egpa, Gr])
    if ce not in meta_year or yr >= meta_year[ce]:
        ll = LOC.get((r["cds14"] or "").zfill(14)) or (None, None)
        meta[ce] = [r["school_name"], r["city"], r["county"], r["cds14"], ll[0], ll[1]]; meta_year[ce] = yr
for k in panel: panel[k].sort()

# ---- metric metadata (X-axis academic/context + selectable outcome rates) ----
# num/den letters map to panel array indices in index.html: A=1 D=2 E=3 C=4 G=5 H=6 Gp=10 Gr=14
# `group` labels the <optgroup> a metric sits under in the menus (outcome rates are grouped by
# denominator, so the same funnel stage can be read per applicant, per graduate, per A-G completer
# or per student enrolled, side by side).
G_ACAD = "School achievement (all students)"; G_GPA = "Applicant & admit GPA (UC)"; G_UCX = "UC outcomes as indicators (any campus)"
G_CTX = "Context"; G_APP = "Per applicant / per admit"; G_GRAD = "Per graduate (CDE diploma graduates, classes of 2017+)"
G_ELIG = "Per A–G completer (UC/CSU-eligible graduates)"; G_HEAD = "Per student enrolled (grades 9–12)"; G_OUT = "After enrollment (entrants to this campus)"
METRICS = [
  # academic / context (typical X-axis)
  {"key":"avg",  "group":G_ACAD,  "label":"CAASPP proficiency — avg % met (gr 11)", "short":"CAASPP avg % met", "role":"academic",   "fmt":"pct"},
  {"key":"ela",  "group":G_ACAD,  "label":"CAASPP ELA — % met (gr 11)",  "short":"CAASPP ELA % met",  "role":"academic",   "fmt":"pct"},
  {"key":"math", "group":G_ACAD, "label":"CAASPP Math — % met (gr 11)", "short":"CAASPP Math % met", "role":"academic",   "fmt":"pct"},
  {"key":"ag",   "group":G_ACAD, "label":"A–G completion — % of cohort UC/CSU-eligible", "short":"A–G completion", "role":"academic", "fmt":"pct", "num":"G", "den":"C"},
  {"key":"upp",  "group":G_CTX,  "label":"Unduplicated pupils — UPP % (FRPM/EL/foster, gr 9–12)", "short":"UPP %", "role":"context", "fmt":"pct"},
  {"key":"awpe", "group":G_CTX, "label":"Writing req. met — ELWR/AWPE (enrollees)", "short":"ELWR/AWPE", "role":"context", "fmt":"pct",
                 "caveat":"UC enrollees only (self-selected, small N); latest year available per school."},
  {"key":"dist", "group":G_CTX, "label":"Distance to this campus (straight-line miles)", "short":"Distance to campus", "role":"context", "fmt":"mi",
                 "caveat":"Great-circle distance from the school's CDE directory coordinates to the selected campus. Students are likelier to apply to campuses near home, so distance is one way to check whether two schools' funnel rates are comparable; it changes with the campus selector."},
  {"key":"app_gpa","group":G_GPA,"label":"Applicant GPA — UC weighted-capped (gr 10–11)","short":"Applicant GPA","role":"academic","fmt":"gpa",
                 "caveat":"Mean UC-recalculated GPA of the school's UC freshman APPLICANTS (weighted, honors-capped). An applicant-pool measure — distinct from CAASPP, which covers all grade-11 students."},
  {"key":"adm_gpa","group":G_GPA,"label":"Admit GPA — UC weighted-capped (admitted students)","short":"Admit GPA","role":"academic","fmt":"gpa",
                 "caveat":"Mean GPA of ADMITTED students. Partly downstream of the admit decision (a more selective campus shows a higher bar), so read it as the GPA level UC accepted at the school, not a pure measure of school strength."},
  {"key":"grad6_prior","group":G_UCX,"label":"UC-wide 6-yr graduation — earlier entrants, any campus (cohorts 6–10 yrs before period)","short":"UC-wide 6-yr grad (prior cohorts)","role":"academic","fmt":"pct","grad":{"col":"g6","win":"prior"},
                 "caveat":"N-weighted 6-yr UC graduation rate of the school's earlier UC entrants (entry cohorts 6-10 years before the selected period starts) - the most recent rates fully observable, and knowable to admissions readers, by decision time. All-UC-campus rates; cohorts shown only when >=10 entrants."},
  # outcome rates (selectable Y-axis); computed period-consistently as ratio-of-sums
  {"key":"ret1_same","group":G_UCX,"label":"UC-wide 1st-year retention — this period's entrants, any campus","short":"UC-wide 1st-yr retention","role":"academic","fmt":"pct","grad":{"col":"r1","win":"same"},
                 "caveat":"Share of the school's UC freshman entrants in the selected period still enrolled after one year (available through entry 2024). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"grad4_same","group":G_UCX,"label":"UC-wide 4-yr graduation — this period's entrants, any campus","short":"UC-wide 4-yr grad","role":"academic","fmt":"pct","grad":{"col":"g4","win":"same"},
                 "caveat":"4-year UC graduation rate of entrants in the selected period; mature only through entry 2021 (empty for recent periods - try 2016-2019). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"grad6_same","group":G_UCX,"label":"UC-wide 6-yr graduation — this period's entrants, any campus","short":"UC-wide 6-yr grad","role":"academic","fmt":"pct","grad":{"col":"g6","win":"same"},
                 "caveat":"6-year UC graduation rate of entrants in the selected period; mature only through entry 2019 (empty for recent periods - try 2016-2019). SCOPE: counts the school's entrants to ANY UC campus (pooled), not only the selected one - so a school can carry a rate even when its admits/enrollees to this campus are zero or suppressed."},
  {"key":"admit_rate","group":G_APP, "label":"Admit rate to this campus (admits ÷ applicants)",        "short":"Admit rate",        "role":"outcome","fmt":"ratio","num":"D","den":"A"},
  {"key":"yield",     "group":G_APP, "label":"Enrollment yield (enrollees ÷ admits)",      "short":"Yield (enroll÷adm)","role":"outcome","fmt":"ratio","num":"E","den":"D"},
  {"key":"app_per_grad","group":G_GRAD,"label":"Applicants ÷ graduates (share of the class applying)","short":"Apps ÷ graduates","role":"outcome","fmt":"ratio","num":"A","den":"Gr",
                 "caveat":"Graduates = the school's regular-diploma graduates in the class of the admission year (CDE four-year cohort × diploma rate), available for classes of 2017 on. Applicants are UC's count of the school's freshman applicants to this campus; the two come from different agencies, so treat the ratio as a school-level indicator."},
  {"key":"adm_per_grad","group":G_GRAD,"label":"Admits ÷ graduates (share of the class admitted)",    "short":"Admits ÷ graduates","role":"outcome","fmt":"ratio","num":"D","den":"Gr",
                 "caveat":"Admits per graduate = (admits ÷ applicants) × (applicants ÷ graduates): it folds the school's application behaviour into the campus's decision. Graduates available for classes of 2017 on."},
  {"key":"enr_per_grad","group":G_GRAD,"label":"Enrollees ÷ graduates (share of the class enrolling)",  "short":"Enroll ÷ graduates","role":"outcome","fmt":"ratio","num":"E","den":"Gr",
                 "caveat":"Enrollees per graduate = yield × admit rate × application rate. Graduates available for classes of 2017 on."},
  {"key":"app_rate",  "group":G_ELIG,"label":"Applicants ÷ A–G completers (application rate)","short":"Apps ÷ A–G completers",  "role":"outcome","fmt":"ratio","num":"A","den":"Gp"},
  {"key":"adm_per_elig","group":G_ELIG,"label":"Admits ÷ A–G completers",                    "short":"Admits ÷ A–G completers", "role":"outcome","fmt":"ratio","num":"D","den":"Gp"},
  {"key":"enr_per_elig","group":G_ELIG,"label":"Enrollees ÷ A–G completers",                 "short":"Enroll ÷ A–G completers", "role":"outcome","fmt":"ratio","num":"E","den":"Gp"},
  {"key":"app_per_head","group":G_HEAD,"label":"Applicants ÷ grade 9–12 enrollment",       "short":"Apps ÷ enrollment", "role":"outcome","fmt":"ratio","num":"A","den":"H"},
  {"key":"adm_per_head","group":G_HEAD,"label":"Admits ÷ grade 9–12 enrollment",           "short":"Admits ÷ enrollment","role":"outcome","fmt":"ratio","num":"D","den":"H"},
  {"key":"enr_per_head","group":G_HEAD,"label":"Enrollees ÷ grade 9–12 enrollment",        "short":"Enroll ÷ enrollment","role":"outcome","fmt":"ratio","num":"E","den":"H"},
  {"key":"ret1_camp","group":G_OUT,"label":"1st-year retention at this campus — this period's entrants","short":"Retention (this campus)","role":"outcome","fmt":"pct","grad":{"col":"r1","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Retention is available through entry 2024."},
  {"key":"grad4_camp","group":G_OUT,"label":"4-yr graduation at this campus — this period's entrants","short":"4-yr grad (this campus)","role":"outcome","fmt":"pct","grad":{"col":"g4","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Mature only through entry 2021 (empty for recent periods - try 2016-2019)."},
  {"key":"grad6_camp","group":G_OUT,"label":"6-yr graduation at this campus — this period's entrants","short":"6-yr grad (this campus)","role":"outcome","fmt":"pct","grad":{"col":"g6","win":"same","src":"campus"},
                 "caveat":"Entrants to the SELECTED campus only (UC dashboard per-campus series). A school-year is reported only when >=10 of its students entered this campus that fall, so mostly larger feeder schools appear - far fewer dots than other outcomes. Mature only through entry 2019 (empty for recent periods - try 2016-2019)."},
]

# ---- periods (presets + single years) ----
PERIODS = [
  {"key":"p2325","label":"2023–2025 (recent, test-blind)","years":[2023,2024,2025]},
  {"key":"p1619","label":"2016–2019 (pre-test-blind)","years":[2016,2017,2018,2019]},
] + [{"key":f"y{y}","label":str(y),"years":[y]} for y in (2025,2024,2023,2022,2021,2020,2019,2018,2017,2016)]
DEFAULT_PERIOD = "p2325"

# ---- write: a small core (data.js) plus data parts the pages fetch on demand ----
# data.js carries everything the explorer needs before its first chart except the panel; the
# panel is split so the default view (one campus) costs one campus part plus the school part:
#   data_parts/schools.js      per school-year covariates [C,Gc,H,ela,math,upp,Gp,Gr], stored
#                              once (they are the same under every campus - asserted below)
#   data_parts/campus_<i>.js   that campus's funnel [A,D,E,agpa,dgpa,egpa] per school-year
#   data_parts/uc_outcomes.js  grad, gradC and tests (the profile card and the UC-outcome axes)
# ucparts.js joins a campus part with the school part back into the row layout above.
from siteparts import pack, write_core, write_part
PARTS_DIR = os.path.join(REPO, "data_parts"); GEN = "scripts/make_site_data.py"
COV = (4, 5, 6, 7, 8, 9, 10, 14)      # covariate slots of a panel row
FUN = (0, 1, 2, 3, 11, 12, 13)        # year + funnel slots
cov = {}                              # (ceeb, year) -> covariate tuple
for key, rows in panel.items():
    ce = key.split("|")[1]
    for row in rows:
        c = tuple(row[i] for i in COV)
        prev = cov.setdefault((ce, row[0]), c)
        assert prev == c, f"covariates differ between campuses for {ce} {row[0]}: {prev} vs {c}"
cov_by_school = defaultdict(list)
for (ce, yr), c in sorted(cov.items()):
    cov_by_school[ce].append((yr,) + c)
school_ceebs = list(cov_by_school)
schools_part = {
  "cols": ["year", "C", "Gc", "H", "ela", "math", "upp", "Gp", "Gr"],
  "ceebs": school_ceebs,
  "data": [[pack([r[i] for r in cov_by_school[ce]]) for i in range(9)] for ce in school_ceebs],
}
part_sizes = {"schools": write_part(os.path.join(PARTS_DIR, "schools.js"), "site:schools", schools_part, GEN)}
for ci, cname in enumerate(CAMPUSES):
    pre = f"{ci}|"
    ceebs = [k[len(pre):] for k in panel if k.startswith(pre)]      # the panel's own order
    campus_part = {
      "campus": ci, "name": cname,
      "cols": ["year", "A", "D", "E", "agpa", "dgpa", "egpa"],
      "ceebs": ceebs,
      "data": [[pack([r[i] for r in panel[pre + ce]]) for i in FUN] for ce in ceebs],
    }
    part_sizes[f"campus_{ci}"] = write_part(os.path.join(PARTS_DIR, f"campus_{ci}.js"), f"site:campus_{ci}", campus_part, GEN)
outcomes_part = {
  "cols": ["entry_year", "N", "ret1", "g4", "g5", "g6"],
  "grad":  {k: [pack([r[i] for r in rows]) for i in range(6)] for k, rows in grad.items()},
  "gradC": {k: [pack([r[i] for r in rows]) for i in range(6)] for k, rows in gradC.items()},
  "tests": tests,
}
part_sizes["uc_outcomes"] = write_part(os.path.join(PARTS_DIR, "uc_outcomes.js"), "site:uc_outcomes", outcomes_part, GEN)

UCDATA = {
  "generated": GENERATED,
  "startYear": START,
  "campuses": CAMPUSES,
  "campusLL": [CAMPUS_LL[c] for c in CAMPUSES],
  "meta": meta,
  "awpe": awpe,
  "metrics": METRICS,
  "periods": PERIODS,
  "defaultPeriod": DEFAULT_PERIOD,
  # the parts and where they live (relative to data.js); ucparts.js loads them on demand
  "parts": {"base": "data_parts/", "schools": "schools.js", "ucOutcomes": "uc_outcomes.js",
            "campus": [f"campus_{ci}.js" for ci in range(len(CAMPUSES))]},
}
core_size = write_core(os.path.join(REPO, "data.js"), "UCDATA", UCDATA, GEN)

# ---- tidy unified CSV for the DEFAULT pooled period ----
IDX = {"A":1,"D":2,"E":3,"C":4,"G":5,"H":6,"Gp":10,"Gr":14}
def jsum(rows, num, den):
    sn = sd = 0.0; ok = False
    for row in rows:
        a = row[IDX[num]]; b = row[IDX[den]]
        if b is None: continue
        if den in ("H", "Gr") and a is not None and a > b: continue   # funnel count exceeds the base: corrupted row
        if a is not None: sn += a; sd += b; ok = True
    return (sn, sd) if (ok and sd > 0) else (None, None)
import math as _math
def dist_mi(ceeb, ci):
    md = meta.get(ceeb); la, lo = (md[4], md[5]) if md else (None, None)
    if la is None or lo is None: return None
    la2, lo2 = CAMPUS_LL[CAMPUSES[ci]]
    p1, p2 = _math.radians(la), _math.radians(la2); dp = p2 - p1; dl = _math.radians(lo2 - lo)
    h = _math.sin(dp/2)**2 + _math.cos(p1)*_math.cos(p2)*_math.sin(dl/2)**2
    return round(2 * 3958.8 * _math.asin(_math.sqrt(h)), 1)
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
        "graduates","apps_per_graduate","admits_per_graduate","enr_per_graduate","distance_mi",
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
    nm, city, cty, cds = meta.get(ce, ["","","","",None,None])[:4]
    aw = awpe.get(ce, [None, None])
    agpa_m = meanof(rows, 11); dgpa_m = meanof(rows, 12)
    out.append([CAMPUSES[ci], ce, cds, nm, city, cty, sumA, sumD, sumE,
        rate(rows,"D","A",True), rate(rows,"E","D",True), rate(rows,"A","Gp",False),
        rate(rows,"D","Gp",False), rate(rows,"E","Gp",False), rate(rows,"A","H",False),
        rate(rows,"D","H",False), rate(rows,"E","H",False),
        sum(r[14] for r in rows if r[14] is not None) or None,
        rate(rows,"A","Gr",False), rate(rows,"D","Gr",False), rate(rows,"E","Gr",False), dist_mi(ce, ci),
        round(ela,1) if ela is not None else None, round(math,1) if math is not None else None, avg, agpct,
        round(upp,1) if upp is not None else None,
        "Y" if (upp is not None and upp >= 75) else "N", aw[0], aw[1],
        round(agpa_m,2) if agpa_m is not None else None, round(dgpa_m,2) if dgpa_m is not None else None,
        *grad_pool(ce, "g6", set(range(min(dp)-10, min(dp)-5))), *grad_pool(ce, "r1", set(dp))])
out.sort(key=lambda r: (r[0], -(r[6] or 0)))
with open(os.path.join(DATA, "cross_section_all9.csv"), "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(cols); w.writerows(out)

# ---- report ----
size = core_size + sum(part_sizes.values())
print(f"panel keys (campus×school): {len(panel)}")
print(f"school meta (unique CEEB)  : {len(meta)}")
print(f"AWPE schools               : {len(awpe)}")
print(f"located schools (lat/lon)  : {sum(1 for v in meta.values() if v[4] is not None)} of {len(meta)}")
print(f"school-years with graduates: {sum(1 for rows in panel.values() for row in rows if row[14] is not None)}")
print(f"grad-rate schools (All-UC) : {len(grad)} | campus-specific keys: {len(gradC)}")
print(f"data.js + data_parts/      : {size/1024/1024:.2f} MB  (core {core_size/1024:.0f} KB; "
      + "; ".join(f"{k} {v/1024:.0f} KB" for k, v in part_sizes.items()) + ")")
print(f"cross_section_all9 rows     : {len(out)} (default period {dp})")
yrs = sorted({row[0] for rows in panel.values() for row in rows})
print(f"years in panel             : {yrs}")
