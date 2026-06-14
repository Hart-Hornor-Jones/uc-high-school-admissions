# Data Cleaning: Implausible "Rate" Values in the UC-Merit Panel
**Date:** 2026-06-07 · **Scope:** every derived rate in `school_year_panel` and `panel_all9_by_year`

## TL;DR

The implausible rates you spotted (Castro Valley admits-per-A-G-eligible = 3.17, etc.) are **not admissions data errors and not build errors.** They trace to a single corrupted input: the **"Met UC/CSU Grad Req's" (A-G eligible) count in CDE's raw ACGR files**, which for certain school-years collapses to a near-zero value while everything around it stays normal. The build ingested these faithfully (verified: 0 mismatches in 20,759 cells against an independent re-parse of the raw files), so the wrongness is in CDE's published source.

The five cases you named are the visible tip. A systematic scan of all 25,114 A-G school-year cells found **1,220 corrupted-denominator cells** of which **only ~60 ever produced a rate > 1** — the other **~1,160 stayed below 1 and would pass any eyeball check while still corrupting any rate or correlation that uses them.** A further 7,003 cells have denominators too small (<10 eligible) to support a stable rate.

**Everything else is clean.** No admits > applicants, no enrollees > admits, no out-of-range CAASPP / UPP / GPA, no negatives. The A-G denominator is the *only* systematic anomaly family.

After cleaning, impossible per-eligible rates fall from **61 → 0** (Berkeley+San Diego panel) and **368 → 6** (all-9 panel; the 6 survivors all have ≥10 eligible and are flagged for review). The project's **headline correlations are unaffected** — they use CAASPP %-met, not A-G — and the A-G-based correlations barely move, so the substantive findings are robust.

---

## 1. The cases you flagged — confirmed and diagnosed

Each is a **correctly-matched school** (same CDS code, stable cohort across all years) with **one isolated year** where the A-G-eligible count craters. The fingerprint is unmistakable: a ~95% regular-diploma rate paired with a ~0–5% A-G rate — logically near-impossible, since A-G completers are a subset of diploma graduates.

| School | Year | Cohort | A-G eligible (raw) | A-G eligible, adjacent yrs | Your rate | Diagnosis |
|---|---|---|---|---|---|---|
| Castro Valley High | 2024 | 677 | **6** | 479 ('23), 447 ('25) | 3.17 / 3.83 | one-year collapse |
| William S. Hart High | 2024 | 436 | **8** | 256 ('22), 277 ('25) | 1.25 | one-year collapse |
| Abraham Lincoln High (Sacramento) | 2019 | 464 | **1** | 211 ('18), 225 ('20) | 11.0 / 5.0 | one-year collapse |
| Santa Monica High | 2019 | 699 | **35** | 472 ('18), 473 ('20) | 1.51 / 1.46 | one-year collapse |
| University Preparatory (Victor Valley) | 2018 | 178 | **13** | 32 ('17) → 88 ('19) → 167 ('24) | 1.00 | early under-report on a ramping charter |

I confirmed each value is **literally present in the raw CDE file** (e.g., `acgr24.txt`, Castro Valley row: cohort 677, regular-diploma 654 = 96.6%, Met-UC/CSU = 6 = 0.9%, and every demographic subgroup sums to that 6). So the build did not mangle it; CDE published it.

---

## 2. Root cause

CDE's "Met UC/CSU Grad Req's" indicator is built from **CALPADS course-completion records**. When a district's A-G course data fails to load for a school in a given submission window, CDE still publishes the school — with a normal cohort and diploma count, but a near-zero A-G count. This is a known class of CALPADS data-quality failure; the re-released file versions in your own folder (`acgr22-v3`, `acgr23-v2`) are CDE itself reissuing years to fix such problems.

Two tells separate a **reporting error** from a **genuinely low-A-G school**:

- **Error fingerprint:** high regular-diploma rate (≥80%) **but** near-zero A-G rate, and/or an isolated drop against the school's own healthy history.
- **Real low-A-G school** (continuation, alternative, workforce): **low diploma rate too.** The detector deliberately does *not* flag these (e.g., San Diego Workforce Innovation, cohort ~1,000, A-G ~2% — but diploma only ~23%, so it's real, not an error).

This is why the errors **cluster by year for different schools** rather than being random: each year's CALPADS submission has its own set of districts/schools whose course data didn't post. Error cells are spread evenly across 2017–2025 (118–156 per year), with a mild bump in 2019–2021 (the COVID submission window).

---

## 3. The systematic scan

I re-parsed all nine raw ACGR files (recovering cohort, regular-diploma, and Met-UC/CSU per school), verified the parse against the build (0/20,759 mismatches), then classified every A-G school-year cell into a mutually-exclusive taxonomy.

| Class | Cells | What it is | Recommended action |
|---|---:|---|---|
| **ONE_YEAR_COLLAPSE** | 175 | School normally healthy; an isolated year craters to ~0 A-G (rate ≤8% vs a healthy baseline) | **Suppress** the per-eligible rate; **impute** a peer-based estimate where both neighbouring years are healthy (79 of 175 qualify, "HIGH confidence") |
| **CHRONIC_ZERO** | 1,045 | School reports ~0 A-G **every** year despite a real cohort and high diploma rate (chronic non-reporter); 127 distinct schools | **Suppress** the per-eligible rate (no valid baseline to impute from) |
| **MODERATE_DROP** | 196 | A real but moderate one-year dip (to ≤60% of baseline) — could be a partial under-report or genuine volatility | **Review** (kept at raw value, flagged) |
| **TINY_DENOMINATOR** | 7,003 | Fewer than 10 A-G-eligible — a per-eligible rate is numerically unstable regardless of correctness | **Reliability floor:** don't compute a per-eligible rate |
| NONE (clean) | 16,695 | Passes all checks | Keep |
| **Total** | **25,114** | | |

**269 distinct schools** carry at least one collapse or chronic error.

### The key point: visible tip vs. hidden mass

Of the **1,220 corrupted-denominator cells** (collapse + chronic), only **~60 ever produced a rate > 1**. The other **~1,160 (95%) kept their rate at or below 1** — because the campus happened to admit fewer students than the (already broken) denominator. Those are invisible to a "rate > 1" scan but are just as wrong, and they silently distort:

- the per-eligible funnel rates the site exposes (D/elig, E/elig, A/elig);
- the A-G completion rate when it's used as a **merit / context variable** (a school recorded at 0.9% A-G when it's truly ~70% is a massive false outlier in any scatter).

This is the real payoff of cleaning systematically rather than case-by-case.

---

## 4. What is NOT broken (checked and clean)

The scan also tested every other derived field. All passed:

- **Admissions funnel** — no school-year with admits > applicants, enrollees > admits, or enrollees > applicants (max yield = 1.000). UC's published counts are internally consistent.
- **CAASPP %-met** (ELA/Math/avg) — all within 0–100.
- **UPP %** — all within 0–100. **Admit rate** — all within 0–100. **GPA** — all within plausible range. No negative counts anywhere.

So the cleaning effort is correctly concentrated on the one input that is actually defective.

---

## 5. Resolution — what was done to each anomaly

The philosophy is research-grade and conservative: **suppress unreliable denominators rather than invent values**, and only impute where the true value is essentially certain.

- **Impute (79 cells):** isolated craters with a healthy year on each side — the school's own peer-median A-G rate × that year's cohort gives a tight estimate (Castro Valley 2024 → ~457; Lincoln-Sac 2019 → ~218; Santa Monica 2019 → ~453). Provided as `ag_met_clean`, flagged `impute_confidence = HIGH`.
- **Suppress (1,141 cells):** collapses without two healthy neighbours (e.g., Hart 2024, University Prep 2018 ramp) and all chronic-zero schools. The per-eligible rate is set to NA; a peer-based `ag_met_estimate` is still provided for optional sensitivity analysis, but no value is committed to the data.
- **Review (196 cells):** moderate dips left at their raw value with a flag, for your judgement.
- **Floor (7,003 cells):** <10 eligible — the per-eligible rate is suppressed as numerically unstable, but the raw count is untouched.

Every decision is auditable: the register carries the raw value, the cohort, the diploma rate, the peer-median rate, the estimate, and a one-line evidence string per cell.

---

## 6. Downstream impact

| | school_year_panel (UCB+SD) | panel_all9_by_year (9 campuses) |
|---|---|---|
| Impossible rates (admits > eligible) **before** | 61 | 368 |
| Impossible rates **after** | **0** | **6** |
| Per-eligible rate cells changed | 148 | 752 |
| Denominators suppressed | 365 | 1,512 |

The 6 residual cases in the all-9 panel all have ≥10 eligible and are flagged: five are MODERATE_DROP under-reports (e.g., University Preparatory 2017, 55 admits / 32 eligible = 1.72) and one is genuine mild flexibility (Village Academy 2024, 12 admits / 11 eligible = 1.09 — UC can admit a small number of non-A-G students via admission-by-exception). These are correctly *visible-and-flagged* rather than silently wrong.

**Effect on findings — minimal, which is the reassuring result.** The published headline (admit rate vs **CAASPP %-met**) does not use A-G at all, so it is untouched. For the A-G-completion-as-merit relationship, cleaning barely moves the pooled 2023–25 correlations:

| Campus | r(A-G completion, admit rate) raw → cleaned |
|---|---|
| Berkeley | +0.056 → +0.040 |
| San Diego | −0.142 → −0.156 |
| Santa Barbara | −0.506 → −0.506 |
| Los Angeles | +0.178 → +0.173 |

The pooled cross-section averages three years, so single-year collapses wash out. **Where cleaning matters most is single-year views and per-school funnel rates** — exactly the places the interactive site lets a reader land on one bad cell (e.g., Castro Valley 2024 alone), which is presumably how you found these.

---

## 7. Deliverables

All in `Data Cleaning 2026-06-07/`:

- **`ag_eligibility_cleaned.csv`** — all 25,114 A-G cells with class, severity, recommended action, raw value, estimate, cleaned value, and evidence. The authoritative cleaned denominator.
- **`anomaly_register_ag.csv`** — the 8,419 flagged cells only (same columns), sorted for review.
- **`anomaly_register_panel.csv`** — the 429 panel rows with admits > eligible (the impossible-rate instances), each tagged with whether an A-G collapse explains it.
- **`school_year_panel_CLEANED.csv`, `panel_all9_by_year_CLEANED.csv`** — your panels + `ag_met_clean`, `ag_denominator_reliable`, `ag_anomaly_class`, `admits_per_eligible_raw`, `admits_per_eligible_clean`. Drop-in for re-deriving rates.
- **`ag_reparsed_school_totals.csv`** — the independent raw re-parse (cohort, diploma, met) used to verify the build and detect the errors.
- **`scripts/`** — `ag_reparse.py`, `plausibility_scan.py`, `clean_ag.py`, `downstream_impact.py`. Fully reproducible; thresholds documented at the top of each.

### Suggested use

1. In any per-eligible rate (D/elig, E/elig, A/elig), gate on `ag_denominator_reliable == 1`, or simply use `admits_per_eligible_clean` (already NA where unreliable).
2. When A-G completion is used as a merit/context axis, drop or down-weight cells where `ag_anomaly_class != NONE`.
3. The 196 MODERATE_DROP and the 6 residual >1 cases are the only items needing a human eye; everything else is resolved.

### Caveats

- Imputed values (`impute_confidence = HIGH`) are model estimates, not CDE figures — fine for rate denominators and sensitivity checks, but cite as estimates.
- The CALPADS-non-submission root cause is inferred from a strong internal fingerprint (diploma-vs-A-G divergence, isolation in time, identical values across every demographic rollup in the raw file, and CDE's own file re-releases). If you want belt-and-suspenders, CDE's ACGR "known issues" notes / DataQuest can corroborate specific districts.
