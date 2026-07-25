#!/usr/bin/env python3
"""
scan_local_correlation.py — systematic conditional-correlation scan.

For every campus × period × context variable (achievement = CAASPP avg % met,
outcome = admit rate), estimates the LOCAL (conditional) correlation function.
Context variables cover the tract ACS measures, the school-level student
measures (UPP / %SED / %EL), and the application-behavior measures added with
the page's self-selection tooling: the school's application rate to the campus
(applicants ÷ cleaned A–G eligible, jointly-observed with the same reliability
gate as the page), its application rate to the other eight campuses
(applications sent there ÷ eligible; campus-year applicant counts suppressed in
the source are treated as unobserved), and its raw applicant volume.

    rho(t) = corr( achievement, outcome | context percentile = t )

with a Gaussian kernel on the context PERCENTILE RANK (bandwidth ±12 percentile
points, grid 5–95 by 2.5) — the same estimator as the context page's
"Local correlation" view (context/index.html), implemented independently here
as both a verification target and a reproducible summary table.

Reported per cell: n, overall r, partial r, rho at the 10/20/50/80/90th
percentiles, the curve's min/max (and where), the linear-moderation interaction
(standardized OLS: zy ~ za + zu + za·zu, u = context percentile), and median
effective n. Values are school-level and unweighted, min 30 applicants,
with the main explorer's ratio-of-sums pooling and suppression gate.

Run:  python3 scripts/scan_local_correlation.py
Out:  data/local_correlation_scan.csv
"""
import csv, json, math, os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__)); REPO = os.path.dirname(HERE)
DATA = os.path.join(REPO, "data")

PERIODS = {"p2325": [2023, 2024, 2025], "p1619": [2016, 2017, 2018, 2019]}
GRID = [5 + 2.5 * i for i in range(37)]
BW = 12.0
MINAPPS = 30
COV_MIN = 0.5

# ---------- load data layers ----------
X = json.loads(open(os.path.join(REPO, "context", "data_context.js"), encoding="utf-8")
               .read().split("window.UCCTX = ", 1)[1].rstrip().rstrip(";"))
CIX = {k: i for i, k in enumerate(X["cvars"])}
SIX = {"sed": 1, "el": 2}
ACS_KEYS = [k for k in X["cvars"] if k != "year"]
APP_KEYS = ["app_rate_own", "app_rate_oth", "app_vol"]
CTX_KEYS = ["upp", "sed", "el"] + ACS_KEYS + APP_KEYS

def fnum(x):
    x = (x or "").strip()
    if x in ("", "*", "None", "NaN", "nan"): return None
    try: return float(x)
    except ValueError: return None

# cleaned A-G eligible denominator Gp, exactly as scripts/make_site_data.py builds it
AGCLEAN = {}
for r in csv.DictReader(open(os.path.join(DATA, "ag_eligibility_cleaned.csv"), encoding="utf-8")):
    _mc = (r["ag_met_clean"] or "").strip()
    AGCLEAN[(r["cds14"], int(r["year"]))] = (r["recommended_action"], r["impute_confidence"],
                                             int(float(_mc)) if _mc not in ("", "None") else None)
def gp_of(cds, yr, raw_G):
    rec = AGCLEAN.get((cds, yr))
    if not rec: return raw_G
    action, conf, met_clean = rec
    if action == "SUPPRESS_RATE":
        return met_clean if (conf == "HIGH" and met_clean is not None) else None
    if action == "FLOOR": return None
    return raw_G

panel = defaultdict(list)     # (campus, ceeb) -> rows
apps_by = defaultdict(dict)   # (campus, ceeb) -> {year: applicants}   (cross-campus lookup)
for r in csv.DictReader(open(os.path.join(DATA, "panel_all9_by_year.csv"), encoding="utf-8")):
    ce = str(r["ceeb"]).strip().zfill(6)
    panel[(r["campus"], ce)].append(r)
    _a = (r["applicants"] or "").strip()
    if _a not in ("", "*", "None"):
        yr = int(float(r["year"]))
        apps_by[(r["campus"], ce)][yr] = apps_by[(r["campus"], ce)].get(yr, 0.0) + float(_a)
CAMPUSES = sorted({c for c, _ in panel})

def school_values(campus, years):
    """One record per school: admit rate (gated), CAASPP avg, all context values."""
    out = []
    yset = set(years)
    for (camp, ceeb), rows in panel.items():
        if camp != campus: continue
        rows = [r for r in rows if int(float(r["year"])) in yset]
        if not rows: continue
        apps = sum(fnum(r["applicants"]) or 0 for r in rows if fnum(r["applicants"]) is not None)
        if apps < MINAPPS: continue
        sn = sd = denAll = 0.0; ok = False
        for r in rows:
            a, b = fnum(r["admits"]), fnum(r["applicants"])
            if b is None: continue
            denAll += b
            if a is not None: sn += a; sd += b; ok = True
        if not (ok and sd > 0) or (denAll > 0 and sd / denAll < COV_MIN): continue
        rate = sn / sd
        vs = []
        for r in rows:
            e, t = fnum(r["ela_pct_met"]), fnum(r["math_pct_met"])
            e = None if e is None else round(e, 1); t = None if t is None else round(t, 1)
            if e is not None and t is not None: vs.append((e + t) / 2)
            elif e is not None: vs.append(e)
            elif t is not None: vs.append(t)
        ach = sum(vs) / len(vs) if vs else None
        rec = {"ach": ach, "y": rate}
        # application behavior (page conventions: jointly-observed ratio-of-sums, cov >= 0.5)
        gp_by = {}
        for r in rows:
            g = fnum(r["ag_met_uccsu_count"])
            gp = gp_of(r["cds14"], int(float(r["year"])), None if g is None else int(g))
            if gp is not None: gp_by[int(float(r["year"]))] = gp
        osn = osd = odenAll = 0.0; ook = False
        for r in rows:
            gp = gp_by.get(int(float(r["year"])))
            if gp is None: continue
            odenAll += gp
            a = fnum(r["applicants"])
            if a is not None: osn += a; osd += gp; ook = True
        rec["app_rate_own"] = (osn / osd) if (ook and osd > 0 and (odenAll <= 0 or osd / odenAll >= COV_MIN)) else None
        oa = og = 0.0; got = False
        for yy in years:
            gp = gp_by.get(yy)
            if gp is None: continue
            tot = None
            for c2 in CAMPUSES:
                if c2 == campus: continue
                a2 = apps_by.get((c2, ceeb), {}).get(yy)
                if a2 is not None: tot = (0.0 if tot is None else tot) + a2
            if tot is not None: oa += tot; og += gp; got = True
        rec["app_rate_oth"] = (oa / og) if (got and og > 0) else None
        rec["app_vol"] = apps if apps > 0 else None
        # UPP: admission-year alignment (site convention)
        ups = [fnum(r["upp_pct"]) for r in rows if fnum(r["upp_pct"]) is not None]
        ups = [round(u, 1) for u in ups]
        rec["upp"] = sum(ups) / len(ups) if ups else None
        # ACS + composition: grade-11-year alignment with Y-1 -> Y -> Y-2 fallback, dedup
        for src, table, cols in (("acs", X["ctx"], None), ("sch", X["sch"], None)):
            rows2 = table.get(ceeb) or []
            by = {r2[0]: r2 for r2 in rows2}
            chosen = {}
            for yy in years:
                r2 = by.get(yy - 1) or by.get(yy) or by.get(yy - 2)
                if r2: chosen[r2[0]] = r2
            vals = list(chosen.values())
            if src == "acs":
                for k in ACS_KEYS:
                    xs = [v[CIX[k]] for v in vals if v[CIX[k]] is not None]
                    rec[k] = sum(xs) / len(xs) if xs else None
            else:
                for k, idx in SIX.items():
                    xs = [v[idx] for v in vals if v[idx] is not None]
                    rec[k] = sum(xs) / len(xs) if xs else None
        out.append(rec)
    return out

# ---------- estimator (mirrors context/index.html) ----------
def pct_ranks(vals):
    n = len(vals); idx = sorted(range(n), key=lambda i: vals[i])
    out = [0.0] * n; i = 0
    while i < n:
        j = i
        while j + 1 < n and vals[idx[j + 1]] == vals[idx[i]]: j += 1
        r = (i + j) / 2
        for k in range(i, j + 1): out[idx[k]] = 100 * (r + 0.5) / n
        i = j + 1
    return out

def wcorr(u, a, y, t, h):
    sw = sw2 = swa = swy = 0.0; W = []
    for i in range(len(u)):
        z = (u[i] - t) / h
        if z < -3 or z > 3: continue
        w = math.exp(-0.5 * z * z)
        W.append((i, w)); sw += w; sw2 += w * w; swa += w * a[i]; swy += w * y[i]
    if sw <= 0 or len(W) < 8: return None
    ma, my = swa / sw, swy / sw
    vaa = vyy = vay = 0.0
    for i, w in W:
        da, dy = a[i] - ma, y[i] - my
        vaa += w * da * da; vyy += w * dy * dy; vay += w * da * dy
    if vaa <= 0 or vyy <= 0: return None
    return {"r": vay / math.sqrt(vaa * vyy), "neff": sw * sw / sw2}

def pearson(xs, ys):
    n = len(xs)
    if n < 3: return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sxx = syy = 0.0
    for a, b in zip(xs, ys):
        sxy += (a - mx) * (b - my); sxx += (a - mx) ** 2; syy += (b - my) ** 2
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None

def moderation(u, a, y):
    n = len(u)
    if n < 12: return None
    def z(v):
        m = sum(v) / n; sd = math.sqrt(sum((x - m) ** 2 for x in v) / n) or 1.0
        return [(x - m) / sd for x in v]
    zu, za, zy = z(u), z(a), z(y)
    zi = [za[i] * zu[i] for i in range(n)]
    Xm = [[1.0] * n, za, zu, zi]
    XtX = [[sum(Xm[r][i] * Xm[c][i] for i in range(n)) for c in range(4)] for r in range(4)]
    Xty = [sum(Xm[r][i] * zy[i] for i in range(n)) for r in range(4)]
    A = [XtX[r][:] + [1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
    for c in range(4):
        p = max(range(c, 4), key=lambda r: abs(A[r][c]))
        if abs(A[p][c]) < 1e-12: return None
        A[c], A[p] = A[p], A[c]
        d = A[c][c]; A[c] = [v / d for v in A[c]]
        for r in range(4):
            if r == c: continue
            f = A[r][c]; A[r] = [A[r][j] - f * A[c][j] for j in range(8)]
    Vi = [row[4:] for row in A]
    b = [sum(Vi[r][c] * Xty[c] for c in range(4)) for r in range(4)]
    rss = sum((zy[i] - (b[0] + b[1] * za[i] + b[2] * zu[i] + b[3] * zi[i])) ** 2 for i in range(n))
    se = math.sqrt(rss / (n - 4) * Vi[3][3])
    return {"b": b[3], "t": b[3] / se if se > 0 else None}

def partial_r(rxy, rxz, ryz):
    d = math.sqrt((1 - rxz ** 2) * (1 - ryz ** 2))
    return (rxy - rxz * ryz) / d if d else None

# ---------- scan ----------
def main():
    cols = ["campus", "period", "ctx", "ach", "outcome", "n", "r_overall", "r_partial",
            "rho10", "rho20", "rho50", "rho80", "rho90",
            "rho_min", "rho_min_pct", "rho_max", "rho_max_pct", "mod_beta", "mod_t", "neff_med"]
    out = []
    for period, years in PERIODS.items():
        for campus in CAMPUSES:
            recs = school_values(campus, years)
            for ck in CTX_KEYS:
                tri = [r for r in recs if r["ach"] is not None and r[ck] is not None]
                if len(tri) < 60: continue
                c = [r[ck] for r in tri]; a = [r["ach"] for r in tri]; y = [r["y"] for r in tri]
                u = pct_ranks(c)
                curve = []
                for t in GRID:
                    e = wcorr(u, a, y, t, BW)
                    if e and e["neff"] >= 25: curve.append((t, e["r"], e["neff"]))
                if len(curve) < 10: continue
                def at(t0):
                    return min(curve, key=lambda p: abs(p[0] - t0))[1]
                lo = min(curve, key=lambda p: p[1]); hi = max(curve, key=lambda p: p[1])
                neffs = sorted(p[2] for p in curve)
                mod = moderation(u, a, y)
                rao = pearson(a, y); rco = pearson(c, y); rca = pearson(c, a)
                pr = partial_r(rao, rca, rco) if None not in (rao, rco, rca) else None
                out.append([campus, period, ck, "avg", "admit_rate", len(tri),
                            round(rao, 4), round(pr, 4) if pr is not None else None,
                            round(at(10), 4), round(at(20), 4), round(at(50), 4),
                            round(at(80), 4), round(at(90), 4),
                            round(lo[1], 4), lo[0], round(hi[1], 4), hi[0],
                            round(mod["b"], 4) if mod else None,
                            round(mod["t"], 2) if mod and mod["t"] is not None else None,
                            round(neffs[len(neffs) // 2], 1)])
    dest = os.path.join(DATA, "local_correlation_scan.csv")
    with open(dest, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(cols); w.writerows(out)
    print(f"wrote {len(out)} cells -> {os.path.relpath(dest, REPO)}")

if __name__ == "__main__":
    main()
