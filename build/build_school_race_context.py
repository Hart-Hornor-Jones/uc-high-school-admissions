"""Build data/components/school_race_context.csv — per-school race/ethnicity shares, grades 9-12.

Source: the CDE enrollment compile in `hs data/race_ethnicity/`
(`cde_high_school_race_ethnicity_school_1981_2026.csv`, built 2026-07-08 from CDE's
official historical-enrollment and Census-Day downloads; provenance + SHA-256s in
`cde_enrollment_source_manifest.csv` / `cde_high_school_race_ethnicity_compile_report.json`).

Output grain: cds14 x academic start_year (2013+), one row per school-year with >0
students in grades 9-12. Columns: enr_9_12_total; race_{hisp,white,asian_incl_fil,
black,urg}_pct; race_asian_only_pct. `urg` follows UC's underrepresented-group
definition: Hispanic/Latino + Black/African American + American Indian/Alaska Native
(Pacific Islander NOT included; it adds ~0.4% statewide). `asian_incl_fil` merges
CDE's separate Asian and Filipino categories for comparability with ACS tract "asian".

Join rule used in analysis: admission year Y <-> start_year Y-1 (the entering class's
senior year). Composition is slow-moving, so Y-2 (junior year) is nearly identical.

Verification (2026-07-08): race-category sums reconcile with CUPC gr-9-12 headcounts
(29,110 school-years, median ratio 1.0000, 99.5% within +/-2%, r=1.0000); statewide
shares match CDE published figures; anchor schools correct (Lynbrook 81% Asian,
Compton 84% Hispanic, Piedmont 53% White); panel coverage 99.2% of 2023-25 rows.

Run from the repo root:  python build/build_school_race_context.py
Adjust SRC if the race_ethnicity folder lives elsewhere.
"""
import pandas as pd

SRC = r"..\hs data\race_ethnicity\cde_high_school_race_ethnicity_school_1981_2026.csv"
OUT = "data/components/school_race_context.csv"
MIN_YEAR = 2013

use = ["academic_start_year", "cds_code", "race_ethnicity_standard", "enrollment_9_12"]
df = pd.read_csv(SRC, usecols=use, dtype={"cds_code": str})
df = df[df.academic_start_year >= MIN_YEAR]

w = df.pivot_table(index=["academic_start_year", "cds_code"],
                   columns="race_ethnicity_standard",
                   values="enrollment_9_12", aggfunc="sum").fillna(0)
w["total"] = w.sum(axis=1)
w = w.reset_index().rename(columns={"academic_start_year": "start_year", "cds_code": "cds14"})
w = w[w.total > 0]

out = w[["start_year", "cds14"]].copy()
out["enr_9_12_total"] = w["total"]
out["race_hisp_pct"] = (w["hispanic_latino"] / w["total"] * 100).round(2)
out["race_white_pct"] = (w["white"] / w["total"] * 100).round(2)
out["race_asian_incl_fil_pct"] = ((w["asian"] + w["filipino"]) / w["total"] * 100).round(2)
out["race_black_pct"] = (w["black_african_american"] / w["total"] * 100).round(2)
out["race_urg_pct"] = ((w["hispanic_latino"] + w["black_african_american"]
                        + w["american_indian_alaska_native"]) / w["total"] * 100).round(2)
out["race_asian_only_pct"] = (w["asian"] / w["total"] * 100).round(2)

out.to_csv(OUT, index=False)
print(f"wrote {OUT}: {len(out):,} rows, years {out.start_year.min()}-{out.start_year.max()}")
