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

### `data/trends/gpa_band_counts.csv`, `gpa_cutpoints.csv` — GPA bands (UC IC)
From the "Grad. rates by GPA groups" dashboard: cohorts 2010–2021 × campus (All + 9) ×
{Pell, first-generation, ethnicity} × three GPA bands. Bands are **terciles of that
campus × cohort's own enrollee GPA distribution** (weighted-capped HS GPA for freshmen; transfer
GPA for transfers), so boundaries move across campuses and years — they are data, shown under
the chart and in tooltips. The source publishes graduate **counts** by timing (freshmen: within
4 yrs / 5th yr only / 6th yr only; transfers: within 2 / 3rd only / 4th only) but **no
entering-cohort denominators**:

- Freshman band **rates are not identified**. The page shows the split of graduates by time to
  degree — `share4 = c_first ÷ (c_first+c_second+c_third)`, etc. — masked below 25 graduates.
- Transfer sheets additionally publish the band-level completion **rates** (integer-rounded);
  cumulative values shown are sums of rounded parts (±1 pp per part).
- "Avg" rows in freshman sheets are Tableau-rounded to 0/1 and discarded.
- `*Overall` (no-subgroup) sheets exist only for cohorts 2019–2020.

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
python scripts/make_trends_data.py
```

Each parser writes a `*_qa.json` beside its outputs (row counts, anchor checks, failures).
Verified anchors: systemwide FR 2024 retention 93.0% (N=50,742); 2021 4-yr 74.0%; 2019 6-yr
86.1%; Hispanic/Latinx × Pell 2019 6-yr 77.7% (N=7,976); Berkeley C150_4 = 0.9234 (D=5,431)
in the subgroup vintage file. Tableau crosstab quirks handled by the parsers: tab-delimited
`.csv` in utf-8 **or** utf-16; blank = missing, never zero; thousands separators; `%` suffixes;
the label variants and misspellings listed in the parser headers ("Non-Pell Recipeint").
