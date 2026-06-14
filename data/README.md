# data/ — curated derived datasets

Derived from public UC and CDE records (see repo `README.md` → "Data sources"). Raw downloads
(≈12 GB) are not committed. Full column notes for the legacy panel are in
[`../docs/DATA_DICTIONARY.md`](../docs/DATA_DICTIONARY.md).

| File | Grain | Notes |
|---|---|---|
| `panel_all9_by_year.csv` | campus × school × year | **Master per-year panel**, all 9 campuses, 2015–2025. Funnel + covariates. Powers the site. |
| `dv_admissions_all9.csv` | campus × school × year | Admissions funnel only (applicants/admits/enrollees + admit GPA), all 9 campuses, **1994–2025**. |
| `cross_section_all9.csv` | campus × school | Tidy pooled cross-section for the default period (2023–2025) with every rate computed. |
| `components/` | school × year | Per-year covariates: `caaspp_YYYY.csv` (gr-11 % met), `ag_eligibility.csv` (cohort + UC/CSU-eligible), `upp_lcff.csv` (UPP % + grade 9–12 enrollment). |
| `ceeb_cds_crosswalk.csv` | school | UC CEEB ↔ CDE CDS bridge (~98% hand-verified). |
| `school_year_panel.csv` | campus × school × year | Berkeley & San Diego long panel (verified; includes admit GPA). Superseded for the site by the all-9 panel. |
| `cross_section_summary.csv` | campus | Published per-campus correlations / OLS — the **verification target**. |
| `then_vs_now_*.csv`, `yearly_trend.csv` | campus (× era/year) | Prior published correlation trends. |
| `elwr_school_year_wide.csv` | school × year | ELWR/AWPE writing-requirement rates (UC **enrollees** only; keyed by CEEB). |
| `grad_rates_by_hs.csv` | campus × school × entry year | **UC freshman retention & graduation rates by source high school** (UC Info Center dashboard). `campus` is `All` (all-UC pooled, the well-covered series) or a single campus (big feeders only). Per fall entry cohort 1999–2024: `cohort_n` (shown only when ≥10 entrants), `ret1_pct`, `grad4_pct`, `grad5_pct`, `grad6_pct` (integer %). Maturity: 6-yr through entry 2019, 5-yr 2020, 4-yr 2021, retention 2024. Built by `build/parse_grad_rates.py`; matched to CEEB by name+city+county (1,410/1,423 unique; 13 re-coded schools assigned per-year by DV enrollee activity; 0 unmatched). Validated: campus-level `cohort_n` equals the DV's enrollee count exactly in 94% of Berkeley school-years (r=.997). |

## `panel_all9_by_year.csv` columns

`ceeb, cds14, campus, year, school_name, city, county, applicants, admits, enrollees, admit_rate,`
`adm_gpa, ela_pct_met, math_pct_met, avg_pct_met, ag_cohort, ag_met_uccsu_count, enroll_9_12,`
`upp_pct, lcff_plus, match_method, match_score`

- The funnel (`applicants/admits/enrollees`) is UC; covariates are CDE, joined per year via the
  crosswalk. **Blank ≠ 0** (UC suppresses small cells). CAASPP 2020 is absent (cancelled) and
  2021 is excluded (COVID, non-representative); those years carry funnel + A–G/UPP only.
- Year alignment (matches the original build): CAASPP uses the same year; A–G uses grad cohort
  `(year-1)-(year)`; UPP uses pupil year `(year-1)-(year)`.

## `cross_section_all9.csv` columns (default period 2023–2025)

`campus, ceeb, cds14, school_name, city, county, applicants, admits, enrollees, admit_rate, yield,`
`application_rate, admits_per_eligible, enr_per_eligible, apps_per_enrollment, admits_per_enrollment,`
`enr_per_enrollment, caaspp_ela_pct_met, caaspp_math_pct_met, caaspp_avg_pct_met, ag_completion_pct,`
`upp_pct, lcff_plus, awpe_writing_met_pct, awpe_year, applicant_gpa, admit_gpa,`
`uc_grad6_prior_pct, uc_grad6_prior_n, uc_ret1_same_pct, uc_ret1_same_n`

All rates are ratio-of-sums over jointly-observed years in the period. `admit_rate`/`yield` are %;
the `÷eligible` and `÷enrollment` ratios are unitless.
`uc_grad6_prior_*` is the N-weighted 6-yr UC graduation rate of the school's entrants 6–10 years
before the period (entry 2013–2017 for the default period) with its total cohort N; `uc_ret1_same_*`
is 1st-year retention of the period's own entrants.

## Regenerate

```bash
python3 ../scripts/build_panel_all9.py     # → panel_all9_by_year.csv
python3 ../scripts/make_site_data.py       # → ../data.js (+ cross_section_all9.csv)
```
