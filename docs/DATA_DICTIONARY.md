---
output:
  word_document: default
  html_document: default
---
# UC Admissions Panel: Data Dictionary FULL

---

### `school_year_panel.csv` — the base (57,913 rows)
Grain: **one row per high school × UC campus × year** (Berkeley & San Diego; 1994–2025).

| Column | Meaning |
|---|---|
| `ceeb` | 6-digit UC source-school (high-school) code |
| `cds14` | 14-digit CDE County-District-School code (blank if unmatched) |
| `campus` | `Berkeley` or `San Diego` |
| `year` | UC admission cycle (1994–2025) |
| `school_name`, `city`, `county` | From the UC source-school data |
| `applicants`, `admits`, `enrollees` | counts of students in each category. **Blank = suppressed or not observed — not zero** (UC suppresses cells to avoid identifying particular students) |
| `admit_rate` | `100 × admits / applicants` (blank if either is blank) |
| `adm_gpa` | Mean GPA of the subset of students admitted, where reported |
| `caaspp_year` | grade-11 CAASPP test grafted on. Each entering class is matched to its **own grade-11 test, the prior spring** (`caaspp_year = year − 1`). Spring tests run 2015–2025 except spring 2020 (cancelled, COVID) and spring 2021 (excluded, non-representative) — so CAASPP is blank for the **2021 and 2022** entering classes (and 2015, whose 2014 test predates the series). |
| `ela_pct_met`, `math_pct_met` | Grade-11 **% Standard Met & Above**, school-level, All students |
| `avg_pct_met` | Mean of `ela_pct_met` and `math_pct_met` |
| `ag_year` | year of associated A-G completion observations (graduating cohort `(year-1)-(year)`) |
| `ag_cohort` | graduating-cohort size |
| `ag_met_uccsu_count` | Graduates meeting UC/CSU "a-g" requirements (~ UC-eligible) |
| `admits_per_eligible` | `admits / ag_met_uccsu_count` — **A school-level ratio, not a true per-student rate** (cohorts/sources differ) |
| `cupc_year` | year of pupil count (`(year-1)-(year)`) |
| `enroll_9_12` | CALPADS total grade 9–12 enrollment |
| `upp_pct` | percentage of school's enrollment that is "high-need" students |
| `lcff_plus` | `Y` if `upp_pct ≥ 75%` (LCFF+ school), else `N` |
| `match_method`, `match_score` | how data files were matched |

### `pooled_cross_section_2023_2025.csv` — currated (2,240 rows)
Grain: **one row per campus × school**, pooling the three most recent admission years.

| Column | Meaning |
|---|---|
| `campus`, `ceeb`, `cds14`, `school_name`, `city`, `county` | identifiers |
| `applicants_2325`, `admits_2325` | summed over 2023–2025 |
| `admit_rate_2325` | pooled `100 × admits / applicants` |
| `ela_pct_met_avg`, `math_pct_met_avg`, `avg_pct_met` | mean of available 2023–2025 CAASPP |
| `upp_pct_2425`, `lcff_plus` | from CUPC 2024-25 |
| `ag_cohort_2425`, `ag_met_2425`, `admits_per_eligible` | from A-G 2024-25 |
| `match_method`, `match_score` | traces of the matching process |
