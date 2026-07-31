#!/usr/bin/env python3
"""
make_denied_data.py — build denied/data_denied.js for the admitted-vs-denied page.

Input
-----
data/school_campus_year_admitted_denied.csv
    ceeb x campus (9 + Universitywide) x fall 1994-2025 for CA public high schools:
    applicants, admits, denied, app_gpa, adm_gpa, den_gpa.
    Counts come from the by-year counts tabs (labels verified); GPA from the by-year
    GPA tab with the one-position campus-label offset REPAIRED (see
    build/repair_gpa_offset_20260730.py and docs/CHANGELOG.md 2026-07-30).
    Denied mean GPA = (N_app*GPA_app - N_adm*GPA_adm) / N_denied — exact given the
    published means. Do NOT rebuild this file by joining GPA from school_year_panel.csv
    or school_year_wide.csv per-campus columns (their GPA labels are shifted).

data/dv_admissions_all9.csv
    Supplies the school-name universe (ceeb -> school_name, city, county), identical
    to the naming used everywhere else on the site.

Output
------
denied/data_denied.js  —  window.UCDENIED = {...}, strict JSON payload:
    y0        first year (1994); years run y0 .. y0+nYears-1
    campuses  10 names, Universitywide first (row order of the heatmap wall)
    schools   [ceeb, name, city, county][] sorted by name, index = school id
    series    per school: 10 campus slots, each a list of packed rows
              [yi, app, adm, gm, gd] with yi = year - y0,
              app/adm = counts (-1 = suppressed/absent), gm/gd = GPA*100 (0 = absent).
              denied is NOT stored: it is exactly applicants - admits (asserted here).
    agg       the SAME structure with one campus slot per campus, holding the pooled
              all-California-public-high-schools marginal for that campus x year:
              [yi, app, adm, gm, gd, nSchools]. Used for the "all high schools"
              default selection and as the reference for the wall's relative mode.

Pooled marginal (agg)
---------------------
Over every school-year at that campus where applicants, admits, app_gpa and adm_gpa
are ALL published:
    app  = sum N_app                     adm  = sum N_adm            den = app - adm
    gm   = sum(N_adm*GPA_adm) / adm      (enrollment-weighted admit mean)
    gd   = (sum(N_app*GPA_app) - sum(N_adm*GPA_adm)) / den
The denied pooled mean is the same moment identity applied to the pooled totals, so
it is NOT affected by the per-school den<10 mask: schools masked individually still
contribute their applicant and admit moments here. The counts in an agg row are the
counts of the contributing schools (nSchools), not UC's campus grand total, because
school-years whose GPA is suppressed cannot enter a GPA-weighted mean.

Masking (applied HERE, so the page cannot unmask):
    * den_gpa is kept only when denied >= 10 (below that the derived mean is
      noise-dominated) and 0 < den_gpa < 5 (tiny-denominator artifacts).
    * blank != 0: suppressed cells stay absent, never zero.

Universe: CEEBs present in dv_admissions_all9.csv (1,602 CA public high schools).
Codes outside it (community-college / non-public / unidentifiable CEEBs that ride
along in the counts extract) are dropped; they carry 69 of 129,625 displayable
denied-GPA school-years (0.05%).

Checks (all hard assertions):
    * CEEB traps: 052980 = MISSION SENIOR (SF), 051984 = UNIVERSITY (Irvine),
      052970 = LOWELL (SF); 052904 (San Fernando) must NOT be in the universe map
      under a Mission name.
    * denied == applicants - admits on every kept row where both are present.
    * den_gpa in the CSV re-derives from (app, adm, app_gpa, adm_gpa) to < 5e-9.
"""
import csv, json, math, os, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "school_campus_year_admitted_denied.csv")
DV = os.path.join(ROOT, "data", "dv_admissions_all9.csv")
OUT = os.path.join(ROOT, "denied", "data_denied.js")

Y0, Y1 = 1994, 2025


def g100(v):
    """GPA -> int(GPA*100), rounded exactly as a 2-decimal display would round it.

    The page shows (g100/100).toFixed(2); deriving the int from the '%.2f' string
    makes build rounding and any independent '%.2f' recompute agree digit-for-digit
    (a bare round(v*100) double-rounds and can differ by 1 near .005 boundaries).
    """
    return round(float(f"{v:.2f}") * 100)
CAMPUSES = ["Universitywide", "Berkeley", "Los Angeles", "San Diego", "Irvine",
            "Davis", "Santa Barbara", "Santa Cruz", "Riverside", "Merced"]
CIDX = {c: i for i, c in enumerate(CAMPUSES)}
GENERATED = "2026-07-31"


def f(x):
    return None if x == "" else float(x)


def main():
    # ---- name universe -------------------------------------------------------
    names = {}
    with open(DV, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["ceeb"] not in names:
                names[r["ceeb"]] = (r["school_name"], r["city"], r["county"])
    assert names["052980"][0].startswith("MISSION SENIOR"), "CEEB trap: 052980 must be Mission SF"
    assert names["052980"][1] == "San Francisco"
    assert names["051984"] == ("UNIVERSITY HIGH SCHOOL", "Irvine", "Orange")
    assert names["052970"][0] == "LOWELL HIGH SCHOOL"
    assert "052904" not in names or "MISSION" not in names["052904"][0], \
        "CEEB trap: 052904 is San Fernando, never Mission"

    # ---- read + mask ---------------------------------------------------------
    rows = defaultdict(lambda: defaultdict(dict))  # ceeb -> cidx -> yi -> packed
    # pooled marginal accumulators: (cidx, yi) -> [sum app, sum app*ga, sum adm, sum adm*gm, nSchools]
    pool = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0])
    n_in = n_named = n_kept = n_gd = n_masked_small = 0
    dropped_universe_gd = 0
    with open(SRC, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            n_in += 1
            ceeb = r["ceeb"]
            app, adm, den = f(r["applicants"]), f(r["admits"]), f(r["denied"])
            ga, gm, gd = f(r["app_gpa"]), f(r["adm_gpa"]), f(r["den_gpa"])
            showable_gd = gd is not None and den is not None and den >= 10 and 0 < gd < 5
            if ceeb not in names:
                if showable_gd:
                    dropped_universe_gd += 1
                continue
            n_named += 1
            year, campus = int(r["year"]), r["campus"]
            if not (Y0 <= year <= Y1) or campus not in CIDX:
                continue
            # internal consistency: denied is exactly applicants - admits;
            # den_gpa re-derives from the published means
            if app is not None and adm is not None:
                assert den == app - adm, f"denied != app-adm at {ceeb}/{campus}/{year}"
            if gd is not None:
                assert None not in (app, adm, den, ga, gm) and den > 0
                rd = (app * ga - adm * gm) / den
                assert abs(rd - gd) < 5e-9, f"den_gpa mismatch at {ceeb}/{campus}/{year}"
            if gd is not None and den is not None and den < 10:
                n_masked_small += 1
            # pooled marginal: every school-year with all four published, mask or not
            if None not in (app, adm, ga, gm) and app > 0 and adm >= 0:
                p = pool[(CIDX[campus], year - Y0)]
                p[0] += app; p[1] += app * ga; p[2] += adm; p[3] += adm * gm; p[4] += 1
            gd_keep = gd if showable_gd else None
            packed = [None,
                      -1 if app is None else int(app),
                      -1 if adm is None else int(adm),
                      0 if gm is None else g100(gm),
                      0 if gd_keep is None else g100(gd_keep)]
            if packed[1] < 0 and packed[2] < 0 and packed[3] == 0 and packed[4] == 0:
                continue  # nothing displayable
            packed[0] = year - Y0
            rows[ceeb][CIDX[campus]][year - Y0] = packed
            n_kept += 1
            if packed[4]:
                n_gd += 1

    # ---- assemble ------------------------------------------------------------
    school_list = sorted(rows.keys(), key=lambda c: (names[c][0], names[c][1], c))
    schools, series = [], []
    for ceeb in school_list:
        nm, city, county = names[ceeb]
        schools.append([ceeb, nm, city, county])
        series.append([[rows[ceeb][ci][yi] for yi in sorted(rows[ceeb][ci])]
                       if ci in rows[ceeb] else [] for ci in range(len(CAMPUSES))])

    # ---- pooled marginals ----------------------------------------------------
    agg = []
    for ci in range(len(CAMPUSES)):
        slot = []
        for yi in range(Y1 - Y0 + 1):
            if (ci, yi) not in pool:
                continue
            sapp, mapp, sadm, madm, nsch = pool[(ci, yi)]
            if sapp <= 0 or sadm <= 0:
                continue
            den = sapp - sadm
            gm_p = madm / sadm
            gd_p = (mapp - madm) / den if den >= 10 else None
            assert 0 < gm_p < 5, f"pooled adm gpa out of range {CAMPUSES[ci]}/{Y0+yi}"
            assert gd_p is None or 0 < gd_p < 5, \
                f"pooled den gpa out of range {CAMPUSES[ci]}/{Y0+yi}"
            slot.append([yi, int(round(sapp)), int(round(sadm)),
                         g100(gm_p), 0 if gd_p is None else g100(gd_p), nsch])
        agg.append(slot)

    payload = {"generated": GENERATED, "y0": Y0,
               "nYears": Y1 - Y0 + 1, "campuses": CAMPUSES,
               "schools": schools, "series": series, "agg": agg}
    body = json.dumps(payload, separators=(",", ":"), allow_nan=False)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("/* Auto-generated by scripts/make_denied_data.py — do not edit by hand. */\n")
        fh.write("window.UCDENIED = ")
        fh.write(body)
        fh.write(";\n")

    print(f"rows in: {n_in:,}; in universe: {n_named:,}; kept: {n_kept:,}")
    print(f"schools: {len(schools):,}")
    print(f"denied-GPA values shown: {n_gd:,}; masked small-denominator (den<10): {n_masked_small:,}")
    print(f"displayable denied-GPA school-years dropped with out-of-universe CEEBs: {dropped_universe_gd}")
    print(f"pooled marginal rows: {sum(len(s) for s in agg):,} "
          f"({', '.join(f'{CAMPUSES[i]}:{len(agg[i])}' for i in range(len(CAMPUSES)))})")
    for ci in (0, 1):
        last = agg[ci][-1]
        print(f"  {CAMPUSES[ci]} {Y0+last[0]}: {last[5]} schools, app {last[1]:,}, "
              f"adm {last[2]:,}, adm GPA {last[3]/100:.2f}, den GPA {last[4]/100:.2f}")
    print(f"wrote {OUT} ({os.path.getsize(OUT)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
