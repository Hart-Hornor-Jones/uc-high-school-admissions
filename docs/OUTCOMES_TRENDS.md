# Outcomes over time (`trends/`) — methods, data & caveats

The `trends/` page plots undergraduate outcome measures across entering cohorts, split by the
populations the public aggregates can distinguish. Everything on the page is precomputed into
`trends/data_trends.js` by `scripts/make_trends_data.py` from the tidy CSVs in `data/trends/`,
which are in turn produced by four parsers in `build/` (runbook at the end).

## Two universes, never mixed in one chart

| | UC Information Center | Federal (IPEDS / College Scorecard) |
|---|---|---|
| Cohort | All new UC freshmen or transfer entrants, by entering year | C150: first-time, full-time bachelor's-seeking fall cohort. Scorecard NSLDS measures: Title IV (federal aid) recipients only. IPEDS completions: degrees conferred |
| Ethnicity | UC categories (Asian/Pacific Islander combined; no two-or-more) | Federal categories (Asian and NHPI separate; two-or-more present) |
| Pell | Receipt in the entering year | Receipt in the entering year |
| First-generation | No parent with a four-year degree | Scorecard: no parent with *any* postsecondary schooling — broader; do not compare levels across universes |
| Used in | Systemwide groups, high schools, community colleges, GPA bands | Campuses, majors, earnings & debt, first-generation curves |

A chart never draws series from both universes. The header badge states the universe of the
current view.

## Datasets and grains

### `data/trends/sys_rates.csv` — systemwide trajectories (UC IC)
Grain: `level (FR/TR) × slice × ethnicity × pell × first_gen × cohort × measure`.
From the UG-Outcomes "Graduation rates" dashboard crosstabs (systemwide only; includes
intercampus transfers). Freshman cohorts 2000–2024; transfer cohorts 1999–2024. Measures:
`ret1` (enrolled at start of year 2), cumulative `grad3/4/5/6` and `grad7p` (FR),
`grad2/3/4` and `grad5p` (TR), `grad6_nonuc` (UC **or** non-UC degree within 6 years,
cohorts 2010–2019), `ttd_mean` (mean years to degree among graduates), `gradgpa_mean`
(mean final UC GPA among graduates, weighted across time-to-degree groups; `n` = graduates).
Rates carry the published cohort `n`. Follow-up is mechanical: a 6-year rate exists only for
cohorts entering by 2019, a 4-year rate by 2021, retention by 2024.

Slices harvested: all-demographics, ethnicity, ethnicity×Pell (from 2003), ethnicity×first-gen
(from 2000). The dashboard publishes **no plain Pell or first-gen slice**, so the site's Pell and
first-generation lines (`slice = agg`) are N-weighted combinations of the ethnicity×Pell
(×first-gen) cells over the full ethnicity partition — exact up to the 0.1-pp rounding of the
published cells; they are built only where at least 5 of the 7 ethnicity cells report. Mean
measures (TTD, GPA) are not aggregated this way (means need graduate counts, not cohort counts)
and remain available under the ethnicity splits.

### `data/trends/hs_series.csv`, `hs_names.csv` — by source high school (UC IC)
Passed through from the repo's validated `data/grad_rates_by_hs.csv` (44,608 rows; campus
("All" + 9) × CEEB × entry year 1999–2024; `cohort_n`, `ret1`, `grad4/5/6` as integer percents;
cells published only when the entering cohort from that school has **N ≥ 10**; per-campus files
cover large feeders only). Names/city/county from the admissions source-school dimension —
the same UC universe the outcomes table was name-matched against (all 1,428 CEEBs named).

### `data/trends/ccc_series.csv`, `ccc_names.csv` — by source community college (UC IC)
Transfer entrants by source CCC: campus × college × entry year 1999–2024; `cohort_n`, `ret1`,
cumulative `grad2/3/4` (integer percents, same N ≥ 10 masking).

### `data/trends/gpa_rates.csv` (+ legacy `gpa_band_counts.csv`, `gpa_cutpoints.csv`) — GPA bands (UC IC)

Primary source is now a **summary-API extraction** of the "Grad. rates by GPA groups" dashboard
(`ug_outcomes_gpa_groups_summary_api_full/vizql_long.csv`), which exposes the underlying
full-precision band **rates** and their **denominators** (numerator ÷ rate; the harvest's
internal check agrees to ~1e-12) for every campus × group × band × cohort cell — including the
per-campus and subgroup × band rates the crosstab export left unidentified. 7,187 tidy rows:
cohorts 2010–2021 × campus (All + 9) × {Pell, first-gen, ethnicity, Overall} × 3 bands, with
numerators, denominators, and increment rates per timing window (FR: within-4 / 5th-only /
6th-only; TR: within-2 / 3rd-only / 4th-only). Cumulative rates are exact sums (shared
denominator).

Key facts, all verified in the build:
- Bands are terciles of the **systemwide** enrollee GPA distribution per cohort and entry type
  (identical boundaries across campus states). Campuses draw very unevenly from them — e.g.
  Berkeley's 2015 freshman entrants split 438 / 1,323 / 3,474 across bands 1/2/3.
- Denominators are the dashboard's own universe: students with a usable GPA — systemwide
  44,173 of the published 46,023 entering cohort at 2019 (≈96%).
- The dashboard's native `*Overall` sheets exist only for cohorts 2019–2020; the build
  synthesizes "Overall" for **all** cohorts as the exact union of the Pell partition
  (numerators and denominators sum; matches the native sheets where both exist).
- Immature cohorts carry real zeros in the later windows; the site omits those cohorts from
  cumulative-5/6-year (and timing-share) measures. Data-driven closure: FR 6-yr through 2019,
  FR 5-yr through 2020; all published transfer windows are closed.
- The legacy crosstab-derived counts (`gpa_band_counts.csv`) and the cutpoint table remain in
  the repo for provenance; the page reads `gpa_rates.csv`.

### `data/trends/ucsd_rates.csv` — UC San Diego deep dive (UCSD IR)

From `ucsd_retention_full_grid/normalized_rates.csv` — a VizQL extraction of UC San Diego's
institutional-research retention/graduation dashboards on the grid demographic family
(ethnicity / first-generation / Pell) × subgroup × **UCSD school/division of major** × entering
cohort (2013–2024). 6,450 unsuppressed cells: FR ret1/ret2 + grad4/5/6; TR ret1 + grad2/3/4/5.
Rates full precision; count = numerator; denominator inferred = cohort cell size. Cells under
the dashboard's reporting threshold are suppressed at source and dropped (1,584). UCSD's own
universe and categories (ethnicity keeps NHPI and Unknown separate; "Chicanx/Latinx") — a third
universe, never mixed with UC IC or federal series in one chart. The FR time-to-degree
distribution worksheet (program-time buckets) is not carried. School names deduped (Halicioğlu
unicode variants); "School of Medicine" has no unsuppressed undergraduate cells.

**Synthesized STEM / non-STEM aggregates.** Because every cell carries a numerator and a
denominator, the build adds two combined "schools": *All STEM schools* (Biology, Engineering,
Physical Sciences, Scripps, Halicioğlu Data Science) and *All non-STEM schools* (Arts &
Humanities, Social Sciences, Global Policy & Strategy) — exact sums of graduates and cohort
sizes over member schools. Public Health (Wertheim), "Special," and Medicine are left
unclassified (mixed or non-degree populations). Suppressed member cells hold at most 9
students, so each combined point is emitted only when the hidden cells could not move the
aggregate rate by more than 1 pp in either direction (1,219 points pass; 538 are withheld,
mostly small ethnic groups × early cohorts). A school counts as expected for a cell only if it
reports that measure for that cohort for any group, so schools that did not yet exist (e.g.
Data Science before 2020) are not treated as missing.

### `data/trends/ucb_rates.csv` — UC Berkeley deep dive (UCB OPAP)

Primary: `berkeley_disaggregated_grad_rates_final/normalized_rates.csv` — a VizQL extraction of
UC Berkeley OPAP's "Disaggregated Grad Rates" dashboard (calviz.berkeley.edu): freshman and
transfer entrants 2010–2023 with full-precision graduation rates, numerators and denominators,
by Overall, **detailed race/ethnicity** (URM; African American; Chicano/Latino with Mexican
American/Chicano and Other Hispanic/Latino separately; Native American; Pacific Islander; Asian
Non-Underrepresented with Chinese, Filipino, Japanese, Korean, South Asian, Vietnamese, Other
Asian; Asian Underrepresented; White; Other/Decline; International), gender (incl. nonbinary),
first-generation, and the campus's **EOP-eligibility markers** (eligible / not / 1–3 markers).
Year-by-Year mode only (the dashboard's 5-yr moving average is a derivable smoothing). Window
gates vs the 2025 vintage: FR 6-yr ≤ 2019, 4-yr ≤ 2021; TR 2-yr ≤ 2023, 4-yr ≤ 2021.

Secondary: `UCB Students - Graduation & Retention Rates.xlsx` (Our Berkeley download): one-year
retention counts by ethnicity × gender × residency and by **entry college** (L&S, Engineering,
Chemistry, Environmental Design, Haas, Rausser/CNR, Other). Rates = retained ÷ (retained + not),
aggregated over residency; marginals and the ethnicity × gender cross are carried; cells under
N = 20 hidden. A fourth universe (Berkeley's own cohorts and categories), never mixed with the
others in one chart. The other Our Berkeley workbooks (majors, GPA by major, admissions, degree
recipients) and the Grad-Rates time-to-degree bucket table (redundant with calviz at coarser
ethnicity) are catalogued but not carried; the "Dashboard Help & Notes" docx holds the
methodology text.

### `data/trends/fed_campus_panel.csv` — campus completion panel (federal)
From the College Scorecard merged institution files (June 10 2026 vintage), UC's nine
undergraduate campuses, data years 1996-97 to 2025-26: `C150_4` overall and by federal race,
by `PELL` / `LOANNOPELL` / `NOLOANNOPELL`, and a derived URM-basic aggregate, with `D150_4*`
denominators; campus rows also carry `RET_FT4`, `PCTPELL`, `FTFTPCTPELL`, `UGDS`.
**Lag caveat:** a C150 value published in data year Y describes a cohort that entered roughly
Y−6. The x-axis is the data year; within-year comparisons are unaffected. Group coverage starts
when the Scorecard starts reporting it (race ~2000s files, Pell splits from the 2016-17 file).

### `data/trends/majors_cip2.csv` — degrees conferred by field (federal)
IPEDS Completions C2012–C2024 (provisional 2023-24), bachelor's degrees, **first majors** only,
aggregated to 2-digit CIP: campus × completions year (period start, 2011–2023) × CIP-2 →
total degrees, degrees to underrepresented students (Black + Hispanic/Latino + AIAN + NHPI,
federal categories, two-or-more excluded), URM share. Counts of degrees conferred — **not**
graduation rates; field mix reflects both enrollment and completion.

### `data/trends/fed_money.csv` — earnings & debt (federal, single vintage)
Scorecard pooled-cohort medians (June 2026 vintage): `MD_EARN_WNE_P6/P8/P10` overall and by
family-income tercile at entry (INC1 $0–30k, INC2 $30–75k, INC3 $75k+), and median cumulative
federal-loan debt of graduates by Pell / non-Pell / first-gen / income groups. A snapshot, not
a time series; Title-IV universe; rendered as a per-campus dot plot.

### `data/trends/fed_firstgen_curves.csv` — first-generation outcome curves (federal)
Scorecard NSLDS: share of (Title-IV) first-generation vs continuing-generation entrants who, by
2/3/4/6/8 years after entry, completed at the original campus, completed after transfer,
withdrew, or remained enrolled. Pooled cohorts per horizon — read as a maturity curve, not a
trend. Scorecard's first-generation definition is broader than UC's.

## Display rules

- Masking: by-school cells are pre-masked at source (N ≥ 10, integer percents); GPA-band timing
  shares hidden below 25 graduates; published cohort sizes shown in tooltips everywhere they
  exist.
- Entering cohorts 2020–2021 are shaded in UC-cohort charts: pandemic disruption, the first
  test-blind cohort (2021), and 2020–21 high-school grade inflation are not separable.
- Small groups (e.g., American Indian entrants, N in the hundreds systemwide) are plotted as
  published but should be read with their Ns.
- Every view has a "Download the numbers shown" CSV; the full tidy CSVs are linked from the
  page's Methods section.

## Reproduce

```
# from the repo root; --corpus points at the outcomes-data corpus
python build/trends_parse_crosses.py    --corpus "<corpus>" --out data/trends
python build/trends_parse_gpa_groups.py --corpus "<corpus>" --out data/trends
python build/trends_parse_schools.py    --repo . --corpus "<corpus>"
python build/trends_parse_fed.py        --corpus "<corpus>" --out data/trends
python build/trends_parse_majors.py     --corpus "<corpus>" --out data/trends
python build/trends_parse_gpa_api.py    --corpus "<corpus>" --out data/trends
python build/trends_parse_ucsd.py       --corpus "<corpus>" --out data/trends
python build/trends_parse_ucb.py        --corpus "<corpus>" --out data/trends
python scripts/make_trends_data.py
```

Each parser writes a `*_qa.json` beside its outputs (row counts, anchor checks, failures).
Verified anchors: systemwide FR 2024 retention 93.0% (N=50,742); 2021 4-yr 74.0%; 2019 6-yr
86.1%; Hispanic/Latinx × Pell 2019 6-yr 77.7% (N=7,976); Berkeley C150_4 = 0.9234 (D=5,431)
in the subgroup vintage file. Tableau crosstab quirks handled by the parsers: tab-delimited
`.csv` in utf-8 **or** utf-16; blank = missing, never zero; thousands separators; `%` suffixes;
the label variants and misspellings listed in the parser headers ("Non-Pell Recipeint").
