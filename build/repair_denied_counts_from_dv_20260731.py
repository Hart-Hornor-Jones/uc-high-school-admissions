#!/usr/bin/env python3
"""
repair_denied_counts_from_dv_20260731.py
Repair the nine per-campus rows of data/school_campus_year_admitted_denied.csv by
taking them from data/dv_admissions_all9.csv instead of the correlation-matrix
wide file.

The defect
----------
The derived denied dataset drew its COUNTS from
    Svetlana/Correlation Matrix 2026-07-05/school_year_wide.csv
and its GPA from a separate (offset-repaired) extract carrying the full CEEB
universe. The wide file was built for the correlation matrix and covers only
1,181 CEEBs; 355 CEEBs that the GPA extract knows about are absent from it
entirely (0 of 355 present, against 1,181 of 1,181 for the schools that work).
Those 355 therefore reached the page with an admitted-GPA series and no volume
at all — and so no derivable denied series, no scatter dot and no grid row.

They are small schools: 85,745 applications against 9,298,231 for the rest
(0.91%); median 158 applications across 1994-2025, against 4,899. But they are
23.1% of the listed school universe, and six of them collide on name+city with a
live code and show as duplicate entries in the school picker (Gompers Prep and
Crawford and Lincoln in San Diego, Aliso Niguel, Lawndale, East Bay Innovation).

Why dv is the right source
--------------------------
dv_admissions_all9.csv carries applicants, admits, app_gpa and adm_gpa for the
nine campuses over the full CEEB universe, with the 2026-07-30 campus-label
offset repair already applied. Against the current CSV it agrees EXACTLY on
every overlapping cell -- 244,944 cells, 0 disagreements on all four fields --
and adds 10,125 applicant and 4,226 admit values the CSV lacks.

What this script changes, and what it deliberately does not
-----------------------------------------------------------
* Nine campus rows, for every CEEB present in dv: replaced wholesale by dv.
  This also DROPS rows the wide file had consolidated onto a modern code from a
  retired one, so those years return to the code they were filed under. Four of
  the six twinned schools reconcile to the application: Gompers 749, Crawford
  1,291, Lincoln 251, East Bay Innovation 326; Aliso Niguel and Lawndale had
  been only partly consolidated, and dv holds more than the wide file did.
* Nine campus rows for CEEBs absent from dv (364 community-college and
  unidentifiable codes) are kept verbatim. They are outside the site's naming
  universe and the page already drops them; rewriting them here would only make
  this file disagree with its other consumers.
* Universitywide rows are kept verbatim for everyone. Universitywide is not the
  sum of the campuses (a student applying to three campuses counts once), the
  wide file is the only source for its counts, and dv has no Universitywide
  column at all -- so the 355 keep a blank systemwide row. That is honest: blank
  means not published here, never zero.
* denied and den_gpa are recomputed from scratch on every row, so the identities
  hold by construction rather than by inheritance.

Run
---
    python3 build/repair_denied_counts_from_dv_20260731.py
then rebuild the page payload:
    python3 scripts/make_denied_data.py
"""
import csv, os, shutil, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "data", "school_campus_year_admitted_denied.csv")
DV = os.path.join(ROOT, "data", "dv_admissions_all9.csv")
BACKUP = os.path.join(ROOT, "data",
                      "school_campus_year_admitted_denied_pre_dv_counts_20260731.csv")

NINE = ["Berkeley", "Los Angeles", "San Diego", "Irvine", "Davis",
        "Santa Barbara", "Santa Cruz", "Riverside", "Merced"]
NINESET = set(NINE)
Y0, Y1 = 1994, 2025
FIELDS = ["ceeb", "campus", "year", "applicants", "admits", "denied",
          "app_gpa", "adm_gpa", "den_gpa"]


def f(x):
    return None if x in (None, "") else float(x)


def num(v):
    """Write counts back the way the file already writes them (36 -> '36.0')."""
    return "" if v is None else f"{float(v):.1f}"


def gpa(v):
    return "" if v is None else f"{v:.10g}"


def derive(app, adm, ga, gm):
    """denied and the denied mean GPA, from the published counts and means."""
    den = None if (app is None or adm is None) else app - adm
    gd = None
    if None not in (app, adm, den, ga, gm) and den > 0:
        gd = (app * ga - adm * gm) / den
    return den, gd


def main():
    if not os.path.exists(SRC) or not os.path.exists(DV):
        sys.exit("missing input: run from the repo with data/ populated")

    # ---- dv: the authority for the nine campuses -----------------------------
    dv = {}
    dv_ceebs = set()
    for r in csv.DictReader(open(DV, newline="", encoding="utf-8")):
        dv_ceebs.add(r["ceeb"])
        if r["campus"] not in NINESET:
            continue
        y = int(r["year"])
        if not (Y0 <= y <= Y1):
            continue
        dv[(r["ceeb"], y, r["campus"])] = (
            f(r["applicants"]), f(r["admits"]), f(r["app_gpa"]), f(r["adm_gpa"]))
    assert dv, "dv carried no nine-campus rows"

    # ---- read the current file, keep what we are not replacing ---------------
    header = None
    keep_uw, keep_nondv = [], []
    old_nine_dv = 0
    old_ceebs = set()
    for r in csv.DictReader(open(SRC, newline="", encoding="utf-8")):
        if header is None:
            header = True
        old_ceebs.add(r["ceeb"])
        if r["campus"] not in NINESET:
            keep_uw.append(r)                       # Universitywide, untouched
        elif r["ceeb"] in dv_ceebs:
            old_nine_dv += 1                        # to be replaced by dv
        else:
            keep_nondv.append(r)                    # outside dv, untouched

    # ---- assemble ------------------------------------------------------------
    out = []
    for r in keep_uw + keep_nondv:
        app, adm, ga, gm = (f(r["applicants"]), f(r["admits"]),
                            f(r["app_gpa"]), f(r["adm_gpa"]))
        den, gd = derive(app, adm, ga, gm)
        out.append({"ceeb": r["ceeb"], "campus": r["campus"], "year": r["year"],
                    "applicants": num(app), "admits": num(adm), "denied": num(den),
                    "app_gpa": gpa(ga), "adm_gpa": gpa(gm), "den_gpa": gpa(gd)})
    added = 0
    for (ceeb, y, campus), (app, adm, ga, gm) in dv.items():
        if app is None and adm is None and ga is None and gm is None:
            continue
        den, gd = derive(app, adm, ga, gm)
        out.append({"ceeb": ceeb, "campus": campus, "year": str(y),
                    "applicants": num(app), "admits": num(adm), "denied": num(den),
                    "app_gpa": gpa(ga), "adm_gpa": gpa(gm), "den_gpa": gpa(gd)})
        added += 1

    out.sort(key=lambda r: (r["ceeb"], r["campus"], int(r["year"])))

    # ---- assertions ----------------------------------------------------------
    seen = set()
    for r in out:
        k = (r["ceeb"], r["campus"], r["year"])
        assert k not in seen, f"duplicate row {k}"
        seen.add(k)
        app, adm, den = f(r["applicants"]), f(r["admits"]), f(r["denied"])
        if app is not None and adm is not None:
            assert den == app - adm, f"denied != app-adm at {k}"
        gd = f(r["den_gpa"])
        if gd is not None:
            ga, gm = f(r["app_gpa"]), f(r["adm_gpa"])
            assert abs((app * ga - adm * gm) / den - gd) < 5e-9, f"den_gpa at {k}"

    shutil.copyfile(SRC, BACKUP)
    with open(SRC, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(out)

    print(f"backup            -> {os.path.basename(BACKUP)}")
    print(f"nine-campus rows replaced from dv: {old_nine_dv:,} -> {added:,}")
    print(f"Universitywide rows kept:          {len(keep_uw):,}")
    print(f"nine-campus rows kept (CEEBs outside dv): {len(keep_nondv):,}")
    print(f"rows written:     {len(out):,}")


if __name__ == "__main__":
    main()
