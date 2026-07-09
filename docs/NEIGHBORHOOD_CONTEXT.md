# Neighborhood-context companion (`context/`) — data & methods

The companion page at `context/` relates three school-level quantities: the **context** of each
California high school — its *surroundings* (tract-level American Community Survey measures) or
its *student body* (UPP, and the grade-11 shares socioeconomically disadvantaged and English
learner) — its students' **measured achievement** (CAASPP grade 11, A–G completion), and its
**UC admissions outcomes** (the same funnel rates as the main explorer). Its motivating question: how much of the
achievement–admissions association is carried by where the school sits?

## Data lineage

1. **School geography.** Source school records (from the CAASPP entity files' CDS codes) are
   joined to the current CDE Public Schools & Districts directory by 14-digit CDS code, giving
   each school a street address and latitude/longitude. High-school records with coordinates are
   submitted to the U.S. Census Geocoder (coordinate batch), yielding the census **tract** (and
   block group) containing the campus — Census 2010 geography for ACS 2015–2019, Census 2020
   geography for ACS 2021–2024. This upstream enrichment lives outside the repo; its slim output
   is committed as `data/components/tract_context.csv` (one row per CDS × year).
2. **ACS context.** For each school-year, tract-level ACS 5-year detailed-table estimates are
   attached with **ACS year = school year** (2025 school years use ACS 2024, the latest
   release). Variables kept: median household income; poverty rate; adult (25+) BA-or-more and
   HS-or-more shares; unemployment rate; median home value; median gross rent; owner-occupancy;
   Hispanic, non-Hispanic White/Black/Asian shares; tract population.
3. **School-level composition.** `build/parse_caaspp_groups.py` reads the CAASPP research files
   and extracts, per school and test year (2016+), the grade-11 **CAASPP-reported enrollment** for
   three student groups — all students, socioeconomically disadvantaged (SED: FRPM-eligible or
   neither parent a high-school graduate), and English learner (excluding reclassified) — yielding
   `data/components/school_group_context.csv` with `sed_pct` and `el_pct`. These are enrollment
   (census) counts, not test outcomes, so they exist even in low-participation years; the 2015
   files do not report per-group enrollment, so the series starts in 2016. A third school-level
   measure, **UPP** (the CALPADS unduplicated FRPM/EL/foster share of grades 9–12), comes directly
   from the main explorer's panel. **Racial/ethnic composition** (added 2026-07): five shares of
   grade 9–12 enrollment from the CDE annual/Census Day enrollment files — Hispanic/Latino, White,
   Asian-or-Filipino (two separate CDE categories, combined for comparability with the ACS tract
   variable), Black/African American, and "URG" (UC's underrepresented-group definition:
   Hispanic/Latino + Black + American Indian) — from `data/components/school_race_context.csv`
   (built by `build/build_school_race_context.py`; series starts spring 2014). Composition shares
   sum over CDE's exclusive categories and reconcile with the CUPC grade-9–12 headcounts
   (median ratio 1.0000 across 29,110 overlapping school-years). These describe a school's
   *students*, not its *applicants* to any campus.
4. **Site data layer.** `scripts/make_context_data.py` joins the slim CSV and the composition CSV
   to the site's school universe (CEEB ↔ CDS from the panel) plus CAASPP **mean scale scores** from
   `data/components/caaspp_*.csv`, and writes `context/data_context.js` (`window.UCCTX`).
   The page loads it alongside the root `data.js`, so every admissions number is *identical*
   to the main explorer's.

## Alignment & composites

- **Year alignment.** Context and test measures for an admission year *Y* are taken from
  the entering class's grade-11 year (*Y*−1), matching the main explorer's CAASPP convention;
  grade-11 SED/EL shares follow the same rule (with the same nearest-year fallback, so classes
  entering 2016 use their senior-year value), while UPP keeps the main explorer's senior-year
  alignment.
  Where that year's join is unavailable — there are no 2020 entity files, affecting classes
  entering in 2021 — the nearest available year substitutes (*Y*−1 → *Y* → *Y*−2; ACS 5-year
  values move slowly, so the substitution is mild). Pooled periods average context over their
  years' chosen values (deduplicated); funnel rates pool by ratio-of-sums exactly as in the
  main explorer (same suppression-reliability gate).
- **SES index.** A plain z-score composite — median income, adult BA share, median home value,
  minus poverty rate, minus unemployment rate — standardized **per year over all California
  public high schools** in the enrichment universe (~2,680/year), so 0 is always "the average
  CA high school's surroundings" and the scale is stable across selections. A school needs ≥3
  of the 5 components to receive a value.
- **CAASPP mean scale scores** (`ela_mean`, `math_mean`) are offered alongside %-met to give a
  finer-grained achievement axis; the spring-2021 administration is excluded (non-representative),
  as in the panel.

## The four views

- **Hold context fixed** — scatter of context (x) vs outcome (y), dots colored by
  achievement; a brushable band on the x-rail conditions on context. Reported: bivariate r's,
  and the **partial correlation** of achievement with the outcome given the context variable
  (residualizing both on context, equivalently the standard partial-r formula), over schools
  with all three values.
- **Local correlation** — the conditional correlation function ρ(achievement, outcome | context = t),
  estimated by kernel-weighted correlation: schools are ranked by the context variable, and at each
  point of a percentile grid (5th–95th, step 2.5) the achievement–outcome correlation is computed
  with Gaussian weights on the context percentile (bandwidth ±12 points by default; slider 6–25).
  Working in rank space keeps the effective sample comparable across a skewed x. Displayed with a
  pointwise 95% interval (Fisher z with kernel effective n = (Σw)²/Σw²), a **no-variation
  envelope** (pointwise 2.5–97.5% band of the curve under 200 seeded permutations of the
  (achievement, outcome) pairs against context ranks — the null of an everywhere-equal
  association), a **linear moderation** summary (standardized OLS zy ~ za + zu + za·zu on the
  context percentile u; the interaction β and t), and optional overlay of all nine campuses.
  `scripts/scan_local_correlation.py` runs the same estimator (independent implementation,
  cross-checked to 4 decimals against the page) over every campus × period × context variable for
  the admit rate and writes `data/local_correlation_scan.csv` — the systematic table behind the
  view.
- **Twin schools** — pairs in near-identical surroundings (within ±4 percentile points of the
  chosen context variable, or sharing a ZCTA / a census tract) whose achievement differs by at
  least a chosen gap; dumbbells compare their outcomes. Pairing is greedy without replacement
  (when two candidate pairs share a school the wider-gap pair wins it). Every pair clearing the
  gap slider is counted, and all reported statistics cover that full population; the chart draws
  an even sample across the context variable (up to 40 rows) when the population is larger.
- **What explains more?** — per campus, R² from OLS of the outcome on context alone,
  achievement alone, and both; displayed as unique-context / joint / unique-achievement shares
  (commonality decomposition). "Joint" is overlap the data cannot attribute to either variable;
  a negative joint share (suppression) is labeled when it occurs.

All statistics are school-level and unweighted, over schools passing the min-applicants filter
(default 30).

## Caveats (also on the page)

- **The tract describes the school's location, not its enrollment.** Choice, transfers,
  magnets and charters break the link between campus tract and student residence — e.g. a
  citywide selective school can sit in a modest tract. Boundary/feeder analyses would need
  student-residence data that public files do not provide.
- ACS 5-year estimates are rolling and carry sampling error at tract scale; medians are
  top-coded ($250k+ income, $2M+ home value). Estimates only; no margins of error in this pass.
- Current CDE coordinates may misplace schools that moved; ~54 of 1,518 site schools (mostly
  closed/relocated) lack context and are absent from this page.
- Ecological, observational associations. Nothing here identifies student-level effects or
  causal direction; the partial correlation conditions on *one* context variable at a time.

## Rebuild

```bash
# systematic conditional-correlation table (after any data change):
python3 scripts/scan_local_correlation.py
# grade-11 composition from the CAASPP research files (only when refreshing the component):
python3 build/parse_caaspp_groups.py --caaspp-dir "/path/to/CAASPP Data" \
    --out data/components/school_group_context.csv
# with the upstream ACS enrichment file available (writes the slim CSV, then the JS):
python3 scripts/make_context_data.py --acs-file /path/to/ca_high_school_rows_with_acs_context.csv
# from the committed CSVs only:
python3 scripts/make_context_data.py --skip-extract
```
