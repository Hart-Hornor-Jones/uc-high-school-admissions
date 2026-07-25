# UC admissions & California high-school academic indicators

An **interactive explorer** and a **reproducible data pipeline** relating each California
high school's academic and demographic indicators to its students' University of California
admission outcomes — across all nine undergraduate campuses, **by admission year or pooled
period**, and across the **full admissions funnel** (apply → admit → enroll) against several
denominators.

> **Live site:** `https://hart-hornor-jones.github.io/uc-high-school-admissions/`


---

## What you can do

Each dot is one California high school, sized by applicants to the selected campus in the
selected period. You can:

- **Pick a campus** (all nine UC undergraduate campuses).
- **Pick a year or period** — individual admission years (2016–2025) or pooled presets
  (2023–2025, 2022–2025 test-blind, 2016–2019 pre-test-blind). Switch it just like campus.
- **Switch views** — a *scatter* (an academic/context metric on x vs. an outcome rate on y, with a
  least-squares fit and a live Pearson *r*), or a Chronicle-style *strip/beeswarm*.
- **Choose the X metric** (academic / context): CAASPP grade-11 proficiency (ELA / Math / average),
  A–G completion, unduplicated pupils (UPP %), or ELWR/AWPE writing.
- **Choose the Y outcome rate** — the admissions funnel against several denominators:
  - **Admit rate** = admits ÷ applicants
  - **Enrollment yield** = enrollees ÷ admits
  - **Application rate** = applicants ÷ A–G eligible
  - **Admits ÷ eligible**, **Enrollees ÷ eligible**
  - **Applicants / Admits / Enrollees ÷ grade 9–12 enrollment** (the headcount denominator)
- **Color** dots by unduplicated-pupil share (UPP gradient) or LCFF+ status; **filter** by minimum applicants;
  **search** any school; **click a dot** for a full profile (every metric + a sparkline of the
  selected rate over time). The campus panel shows how the selected relationship's correlation
  has evolved year by year.

The visual design is modeled on the San Francisco Chronicle's UC-admissions explorer. This is an
**independent project, not affiliated with or endorsed by the Chronicle**, and contains none of
the Chronicle's content.

**Companion page — [`context/`](context/):** adds each school's *context* — tract-level
American Community Survey measures of its surroundings (median income, adult education, poverty,
unemployment, home values, race/ethnicity, and a composite SES index) assigned from the school's
coordinates via the Census Geocoder, school-level student measures (UPP, the grade-11
shares socioeconomically disadvantaged and English learner, and racial/ethnic composition), and
the school's *application behavior* (application rate to the selected campus, application rate to
the other eight campuses, applicant volume) — and asks how much of the achievement–admissions
association each carries. Four
views: a conditioning scatter (brush a band of similar contexts; watch the within-band
achievement→outcome correlation; an optional second hold-fixed variable), a local-correlation
curve (the conditional correlation function,
kernel-estimated across the context distribution, with a permutation no-variation envelope),
matched "twin schools" (near-identical contexts — e.g. similar application rates or volume —
with large achievement gaps: do outcomes differ?),
and a per-campus variance decomposition (R² unique to context, unique to achievement, and joint).
Applicant-pool and admit GPA are selectable outcomes there as well. Methods & caveats:
[docs/NEIGHBORHOOD_CONTEXT.md](docs/NEIGHBORHOOD_CONTEXT.md).

**Companion page — [`trends/`](trends/):** what happens *after* admission, across entering
cohorts back to 1999–2000. One chart, eight comparisons: systemwide graduation/retention/time-to-
degree/final-GPA trajectories split by ethnicity, Pell, first-generation, and their crosses
(UC Information Center data, cohorts 2000–2024); the nine campuses' six-year completion by race
and by Pell/loan status (federal panel, ~1997–2025); per-high-school and per-community-college
outcome series (the same by-school universe as the main explorer); GPA-tercile bands within each
campus×cohort (timing of degrees for freshmen, published band rates for transfers); bachelor's
degrees conferred by major and the underrepresented share (IPEDS 2011–2023); median earnings by
family-income origin and median graduate debt by group (Scorecard). Each chart carries its
universe badge, definitions, cohort sizes, and a CSV download. Methods & caveats:
[docs/OUTCOMES_TRENDS.md](docs/OUTCOMES_TRENDS.md).

---

## The question

Is a California high school's UC admit rate associated with the school's measured academic
strength — and how has that association changed over time? A recurring claim is that the more
selective UC campuses admit a *larger* share of applicants from *lower*-scoring schools. This
repository assembles the relevant **public** data so the claim can be examined empirically, with
explicit attention to confounds (notably applicant self-selection). The tools are descriptive;
read the [caveats](#caveats--how-to-read-the-numbers) and draw your own conclusions.

---

## Headline numbers (pooled 2023–2025, schools with ≥30 applicants)

Pearson correlation between admit rate and CAASPP grade-11 average % met, and the admit-rate gap
between LCFF+ (UPP ≥ 75%) schools and the rest:

| Campus | r(admit rate, proficiency) | LCFF+ minus other (pts) |
|---|--:|--:|
| San Diego | −0.54 | +16.0 |
| Santa Barbara | −0.46 | +6.3 |
| Berkeley | −0.23 | +4.0 |
| Davis | −0.22 | +2.5 |
| Los Angeles | −0.13 | +0.7 |
| Irvine | +0.08 | +0.1 |
| Merced | +0.39 | −2.8 |
| Riverside | +0.48 | −8.9 |
| Santa Cruz | +0.43 | −12.3 |

The pattern is **not uniform**: negative at the selective coastal campuses, near zero at Irvine,
and **positive** at the high-admit inland campuses (Merced, Riverside, Santa Cruz), which admit
most qualified applicants (a capacity dynamic — read them differently). For Berkeley and San Diego
the academic–admit correlation **flipped sign over the past decade** (Berkeley +0.27 in 2015 → −0.26
in 2024; San Diego +0.16 → −0.55); because self-selection is roughly constant across eras, this
time shift helps separate a possible school-level effect from static self-selection.

> The interactive site thresholds on **total applicants**, so its live *r* can differ by ~0.01
> from this table, which (following the source analysis) paired applicants with admits in the
> denominator. The committed data reproduce this table exactly under that convention
> (see [`data/cross_section_summary.csv`](data/cross_section_summary.csv) and the verification in
> [`docs/`](docs/)).

---

## Repository layout

```
.
├── index.html                  # the interactive explorer (self-contained, D3)
├── data.js                     # generated app data (window.UCDATA, per-year panel); rebuilt by scripts/
├── context/                    # companion page: neighborhood context (see docs/NEIGHBORHOOD_CONTEXT.md)
│   ├── index.html              #   conditioning scatter · local correlation · twin schools · variance decomposition
│   └── data_context.js         #   generated (window.UCCTX): tract ACS + CAASPP means; rebuilt by scripts/
├── trends/                     # companion page: undergraduate outcomes over time (see docs/OUTCOMES_TRENDS.md)
│   ├── index.html              #   cohort trend explorer: groups · campuses · schools · GPA bands · majors · money
│   └── data_trends.js          #   generated (window.TRENDS_DATA); rebuilt by scripts/make_trends_data.py
├── data/                       # curated DERIVED datasets (see data/README.md)
│   ├── panel_all9_by_year.csv  #   MASTER: one row per CEEB × campus × year, all 9 campuses, 2015–2025
│   ├── dv_admissions_all9.csv  #   admissions funnel only (apply/admit/enroll), all 9 campuses, 1994–2025
│   ├── cross_section_all9.csv  #   tidy pooled cross-section for the default period (all rates)
│   ├── components/             #   per-year covariates: CAASPP, A–G eligibility, UPP/headcount
│   ├── ag_eligibility_cleaned.csv  #   A–G eligible counts + data-quality flags (the cleaned denominator)
│   ├── ceeb_cds_crosswalk.csv  #   UC(CEEB) ↔ CDE(CDS) bridge
│   ├── school_year_panel.csv   #   Berkeley & San Diego long panel (verified subset, with admit GPA)
│   ├── cross_section_summary.csv  then_vs_now_*.csv  yearly_trend.csv   # prior published summaries
│   └── elwr_school_year_wide.csv  # ELWR/AWPE (UC enrollees)
├── scripts/
│   ├── build_panel_all9.py     # data/dv_admissions_all9 + components  →  data/panel_all9_by_year.csv
│   ├── make_site_data.py       # data/panel_all9_by_year.csv  →  data.js  (+ cross_section_all9.csv)
│   ├── make_context_data.py    # components/tract_context.csv + caaspp means  →  context/data_context.js
│   └── make_trends_data.py     # data/trends/*.csv  →  trends/data_trends.js
├── build/                      # documented upstream pipeline (raw public files → data/)
│   ├── extract_dv_all9.py      #   the one step needing the ~12 GB raw dump → dv_admissions_all9.csv
│   ├── parse_caaspp_groups.py  #   CAASPP research files → grade-11 SED/EL composition (context page)
│   └── README.md               #   runbook
└── docs/                       # methodology & data dictionary
```

---

## Metrics & how rates are computed

For a selected period, each rate is a **ratio of sums** over the years in which both its
numerator and denominator are observed, e.g. admit rate = Σadmits ÷ Σapplicants. This makes
rates comparable across periods of different length and handles UC's cell suppression per rate.
Academic/context metrics (CAASPP, UPP) are averaged over available years; A–G completion is
Σeligible ÷ Σcohort. Applicant/admit/enrollee counts are UC (CEEB); "A–G eligible" and grade
9–12 enrollment are CDE (CDS) — ratios mixing them are school-level indicators, not exact
per-student rates.

**A–G data-quality cleaning.** CDE's published "Met UC/CSU" (A–G eligible) count collapses to
near-zero for a number of school-years — a CALPADS course-data reporting failure (high diploma
rate but ~0% A–G), unrelated to admissions. Left raw it yields impossible "admits ÷ eligible"
rates above 1 and false outliers on the A–G-completion axis. The build substitutes a **cleaned**
A–G eligible count (`data/ag_eligibility_cleaned.csv`): isolated one-year collapses flanked by
healthy years are imputed from the school's own history; collapses without a safe estimate and
chronic non-reporters are **suppressed** (the rate is dropped, not guessed); denominators below
10 eligible are suppressed for per-eligible rates only (the school's real, low completion value
is kept). Method, root-cause evidence, and a per-cell register: [`docs/AG_DATA_CLEANING.md`](docs/AG_DATA_CLEANING.md).

**School-identity (crosswalk) repair.** UC's CEEB codes and CDE's CDS codes share no key, so the
panel joins them by school name. The first-pass fuzzy matcher could glue a school to a similarly
named neighbor (most visibly, Westchester Enriched Sciences Magnets carried West High Torrance's
academic profile). A 2026-07 audit of all 1,549 joins repaired 95 to the school's own CDS record,
set 6 with no valid CDE target to unmatched, and documented the legitimate cases where two UC
records share one CDE campus. Aggregate correlations move by ≤0.01; school-level profiles and
twin pairs are the point. Decision table with evidence: `build/repair_crosswalk_20260725.py`;
method and before/after: [`docs/CROSSWALK_REPAIR.md`](docs/CROSSWALK_REPAIR.md).

---

## Data sources (all public)

Raw source files (≈12 GB) are **not** committed; download them from the agencies below. Only the
compact **derived** datasets are included, under `data/`.

- **UC Information Center** — admissions by source high school (the dependent variable).
  https://www.universityofcalifornia.edu/about-us/information-center
- **UC Information Center — freshman outcomes dashboard** — retention & 4-/5-/6-yr graduation rates
  by source high school (entry cohorts 1999–2024), the basis of the UC-graduation metrics.
- **UC Accountability Report** — systemwide context.
  https://accountability.universityofcalifornia.edu/2025/report.html
- **CDE CAASPP / ELPAC research files** — grade-11 proficiency.
  https://caaspp-elpac.ets.org/caaspp/ResearchFileListSB
- **CDE A–G / graduate completion** — UC/CSU "a–g" eligibility.
  https://www.cde.ca.gov/ds/ad/agcompletiondata.asp
- **CDE CALPADS Unduplicated Pupil Percentage (UPP / LCFF+) & enrollment** — unduplicated-pupil share & headcount.
- **Ed-Data** — school context. https://www.ed-data.org/
- **LAUSD Open Data** — district context. https://opendata.lausd.org/

The crosswalk (`data/ceeb_cds_crosswalk.csv`) bridges the 6-digit CEEB and 14-digit CDS code
universes; hand-verified to ~98%. See [`docs/DATA_DICTIONARY.md`](docs/DATA_DICTIONARY.md).

---

## Reproduce

**Rebuild the site data** from the committed derived files (fast, no raw downloads needed):

```bash
python3 scripts/build_panel_all9.py     # components + funnel  → data/panel_all9_by_year.csv
python3 scripts/make_site_data.py       # panel                → data.js (+ cross_section_all9.csv)
```

**Re-extract the funnel from the raw UC dump** (the only step needing the ~12 GB source):

```bash
python3 build/extract_dv_all9.py /path/to/admissions_source_school_consolidated_lean
```

**Re-parse the UC graduation-rate dashboard crosstabs** (→ `data/grad_rates_by_hs.csv`):

```bash
python3 build/parse_grad_rates.py /path/to/ug_outcomes_freshman_grad_rates_by_hs_internal_control
```

**Rebuild the curated covariates from raw public downloads:** follow [`build/README.md`](build/README.md).

**Preview the site locally:** `python3 -m http.server 8000`, then open http://localhost:8000
(opening `index.html` directly also works — `data.js` is a plain script, not a fetch).

---

## Prior work, inspiration, and attribution

- **Paul Gardiner / SFEDup** previously analyzed UCSD admissions by high school; his published
  data seeded the CEEB↔CDS crosswalk.
- The **San Francisco Chronicle** UC-admissions explorer (Nami Sumida, Hanna Zakharenko) inspired
  the visual design. Independent project; not affiliated with the Chronicle.



---

## Caveats — how to read the numbers

- **UPP & LCFF+.** The "UPP" color axis is the **Unduplicated Pupil Percentage** — the CALPADS/LCFF share of a
  school's students who are low-income (free- or reduced-price-meal eligible), English learners, or foster youth,
  counted once if in more than one category, and so broader than a household-poverty rate. **LCFF+** marks schools
  where that share exceeds 75% of enrollment — the Local Control Funding Formula's high-need threshold for additional
  support.
- **Self-selection.** A negative academic–admit correlation need not, on its own, reflect a school-level
  effect; the over-time view and within-LCFF+ comparisons are the checks against it.
- **Suppression.** UC masks small admit/enroll cells; at Berkeley ~a third of applicant schools
  have suppressed admits, biasing its estimates toward zero. San Diego has more power.
- **Capacity dynamic.** High-admit inland campuses show a *positive* academic–admit correlation
  because they admit most qualified applicants — not a school-level effect.
- **Cross-universe ratios.** Rates dividing UC counts by CDE counts (application rate, ÷eligible,
  ÷enrollment) are school-level indicators, not exact per-student rates.
- **A–G source errors, cleaned.** CDE's A–G-eligible count is corrupted for some school-years
  (near-zero where the school is normally strong); such cells are imputed or suppressed before any
  ÷eligible rate or A–G-completion value is shown — see [`docs/AG_DATA_CLEANING.md`](docs/AG_DATA_CLEANING.md).
- **ELWR/AWPE** reflects UC **enrollees only** (self-selected, often small N), latest year per
  school — indicative only.

This project examines a politically sensitive topic with public data; it aims to be descriptive
and to surface its own limitations rather than to argue a position.
