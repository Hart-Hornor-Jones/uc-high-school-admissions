#!/usr/bin/env python3
"""
make_context_data.py — build the data layer for the neighborhood-context page (context/).

Two stages, both idempotent:

1. EXTRACT (only if the big enrichment file is available): slim the ~87 MB
   ca_high_school_rows_with_acs_context.csv (built by the hs-data pipeline;
   tract-level ACS 5-year context joined to CA high schools via CDE coordinates
   and the Census Geocoder) down to data/components/tract_context.csv —
   one row per (cds14, year) with the kept tract variables. This slim CSV is
   committed, so the repo rebuilds without the big file.

2. BUILD: join the slim CSV + CAASPP mean scale scores (data/components/caaspp_*.csv)
   to the site's school universe (CEEB keys from panel_all9_by_year.csv) and write
   context/data_context.js  (window.UCCTX = {...}).

The context page loads BOTH ../data.js (admissions panel — identical numbers to the
main explorer) and data_context.js. Pooling across a period happens client-side.

ACS year = school year (spring); 2025 rows carry ACS 2024 (latest 5-year release).
The neighborhood SES index is a per-year z-score composite over ALL CA high schools
in the enrichment universe (not just UC-panel schools), so its scale is stable.

Run:  python3 scripts/make_context_data.py [--acs-file PATH]
"""
import argparse, csv, json, math, os, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data"); COMP = os.path.join(DATA, "components")
OUTDIR = os.path.join(REPO, "context")
SLIM = os.path.join(COMP, "tract_context.csv")

# tract variables kept (source column -> slim/short key)
KEEP = [
    ("tract_median_household_income", "inc"),    # $, top-coded 250001
    ("tract_poverty_rate",            "pov"),    # %
    ("tract_pct_bachelors_or_more_25plus", "ba"),# %
    ("tract_pct_high_school_or_more_25plus", "hs"), # %
    ("tract_unemployment_rate",       "unemp"),  # %
    ("tract_median_home_value",       "homeval"),# $, top-coded 2000001
    ("tract_median_gross_rent",       "rent"),   # $
    ("tract_pct_owner_occupied",      "own"),    # %
    ("tract_pct_hispanic",            "hisp"),   # %
    ("tract_pct_nh_white",            "white"),  # %
    ("tract_pct_nh_black",            "black"),  # %
    ("tract_pct_nh_asian",            "asian"),  # %
    ("tract_pop_total",               "pop"),    # count
]
INTS = {"inc", "homeval", "rent", "pop"}
# SES composite components: sign * key (z-scored per year over all CA high schools)
SES = [(1, "inc"), (1, "ba"), (-1, "pov"), (-1, "unemp"), (1, "homeval")]

def fnum(x):
    x = (x or "").strip()
    if x in ("", "*", "NA", "NaN", "nan", "None"): return None
    try:
        v = float(x)
    except ValueError:
        return None
    return None if v < 0 else v          # ACS sentinel negatives (-666666666)

def ceeb6(x):
    x = str(x or "").strip(); return x.zfill(6) if x.isdigit() else x

# ---------- stage 1: extract slim CSV ----------
def extract(acs_file):
    rows = []
    with open(acs_file, encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            yr = (r.get("school_year") or "").strip()
            cds = (r.get("cds_code") or "").strip()
            if not yr or not cds: continue
            out = {"cds14": cds, "year": yr,
                   "acs_year": (r.get("acs_year_used") or "").strip(),
                   "tract_geoid": (r.get("tract_geoid") or "").strip(),
                   "zcta": (r.get("zcta") or "").strip()}
            for src, k in KEEP:
                v = fnum(r.get(src))
                out[k] = ("" if v is None else
                          (str(int(round(v))) if k in INTS else f"{v:.1f}"))
            rows.append(out)
    rows.sort(key=lambda r: (r["cds14"], r["year"]))
    cols = ["cds14", "year", "acs_year", "tract_geoid", "zcta"] + [k for _, k in KEEP]
    with open(SLIM, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)
    print(f"extract: wrote {len(rows)} rows -> {os.path.relpath(SLIM, REPO)}")

# ---------- stage 2: build data_context.js ----------
def build():
    # site universe: ceeb -> cds14 (latest year wins, same rule as make_site_data)
    ceeb_cds = {}; latest = {}
    with open(os.path.join(DATA, "panel_all9_by_year.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            yr = int(float(r["year"])) if r["year"] else 0
            ce = ceeb6(r["ceeb"])
            if ce not in latest or yr >= latest[ce]:
                ceeb_cds[ce] = r["cds14"]; latest[ce] = yr

    # slim context: (cds14, year) -> dict ; per-year z stats over ALL CA high schools
    ctx = {}; peryear = defaultdict(lambda: defaultdict(list))
    geo = {}   # cds14 -> [tract_geoid, zcta] (latest year wins)
    with open(SLIM, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            yr = int(r["year"]); cds = r["cds14"]
            vals = {k: fnum(r[k]) for _, k in KEEP}
            ctx[(cds, yr)] = vals
            if cds not in geo or True:   # rows sorted by year: last wins
                geo[cds] = [r["tract_geoid"], r["zcta"]]
            for _, k in KEEP:
                if vals[k] is not None: peryear[yr][k].append(vals[k])

    zstat = {}   # (year, key) -> (mean, sd)
    for yr, d in peryear.items():
        for k, xs in d.items():
            m = sum(xs) / len(xs)
            sd = math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs)) or 1.0
            zstat[(yr, k)] = (m, sd)

    def ses(yr, vals):
        zs = []
        for sgn, k in SES:
            v = vals.get(k); st = zstat.get((yr, k))
            if v is None or st is None: continue
            zs.append(sgn * (v - st[0]) / st[1])
        return round(sum(zs) / len(zs), 2) if len(zs) >= 3 else None

    # CAASPP mean scale scores: cds14 -> {year: [ela_mean, math_mean]}
    means = defaultdict(dict)
    for fn in sorted(os.listdir(COMP)):
        if not (fn.startswith("caaspp_") and fn.endswith(".csv")): continue
        if fn == "caaspp_2021.csv": continue   # COVID year: ~25% tested; excluded like the panel
        with open(os.path.join(COMP, fn), encoding="utf-8") as fh:
            for r in csv.DictReader(fh):
                em = fnum(r.get("ela_mean")); mm = fnum(r.get("math_mean"))
                if em is None and mm is None: continue
                means[r["cds14"]][int(float(r["year"]))] = [
                    None if em is None else round(em, 1),
                    None if mm is None else round(mm, 1)]

    # assemble per-CEEB
    CVARS = [k for _, k in KEEP] + ["ses"]
    out_ctx = {}; out_geo = {}; out_means = {}
    yrs_seen = sorted({y for _, y in ctx})
    n_ok = 0
    for ce, cds in ceeb_cds.items():
        rows = []
        for yr in yrs_seen:
            vals = ctx.get((cds, yr))
            if not vals: continue
            arr = [yr]
            for _, k in KEEP:
                v = vals[k]
                arr.append(None if v is None else (int(round(v)) if k in INTS else round(v, 1)))
            arr.append(ses(yr, vals))
            rows.append(arr)
        if rows:
            out_ctx[ce] = rows; n_ok += 1
            g = geo.get(cds)
            if g and (g[0] or g[1]): out_geo[ce] = g
        m = means.get(cds)
        if m:
            out_means[ce] = {str(y): v for y, v in sorted(m.items())}

    UCCTX = {
        "generated": datetime.date.today().isoformat(),
        "note": ("Tract-level ACS 5-year context assigned from current CDE school coordinates "
                 "via the Census Geocoder; ACS year = school year (2025 uses ACS 2024). "
                 "SES index = per-year z-score composite (income, BA%, home value, "
                 "minus poverty, minus unemployment) over all CA public high schools."),
        "cvars": ["year"] + CVARS,
        "ctx": out_ctx,        # ceeb -> [[year, inc, pov, ba, hs, unemp, homeval, rent, own, hisp, white, black, asian, pop, ses], ...]
        "geo": out_geo,        # ceeb -> [tract_geoid, zcta]
        "means": out_means,    # ceeb -> {year: [ela_mean, math_mean]}
    }
    os.makedirs(OUTDIR, exist_ok=True)
    dest = os.path.join(OUTDIR, "data_context.js")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("/* Auto-generated by scripts/make_context_data.py — do not edit by hand. */\n")
        fh.write("window.UCCTX = ")
        json.dump(UCCTX, fh, separators=(",", ":"), ensure_ascii=False)
        fh.write(";\n")
    print(f"build: {n_ok}/{len(ceeb_cds)} site schools with tract context; "
          f"{len(out_means)} with CAASPP means -> {os.path.relpath(dest, REPO)} "
          f"({os.path.getsize(dest)/1e6:.2f} MB)")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--acs-file", default=None,
                    help="path to the upstream ca_high_school_rows_with_acs_context.csv (optional)")
    ap.add_argument("--skip-extract", action="store_true")
    a = ap.parse_args()
    if not a.skip_extract and a.acs_file and os.path.exists(a.acs_file):
        extract(a.acs_file)
    elif not os.path.exists(SLIM):
        raise SystemExit("No committed slim CSV and no --acs-file given.")
    else:
        print("extract: skipped (using existing slim CSV)")
    build()
