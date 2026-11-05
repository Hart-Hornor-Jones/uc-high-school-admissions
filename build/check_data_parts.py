#!/usr/bin/env python3
"""
check_data_parts.py - prove the split data layer carries exactly the numbers the pages drew
before the split.

It rebuilds, in Python, the objects each page used to receive in one script (the explorer's
window.UCDATA with its full panel; UCCTX; TRENDS_DATA; UCDENIED) from the new core files
plus data parts, and compares them value for value with reference copies of the old
single-file scripts. Every school, year, campus and variable must be present, and every value
must be equal (floats are compared exactly, not approximately).

usage:
    python3 build/check_data_parts.py --old <checkout of the pre-split site> [--new <repo root>]

The old checkout is any directory holding the previous data.js, context/data_context.js,
trends/data_trends.js and denied/data_denied.js (for example `git worktree add ../old main`).
Exit status 0 means every value matched.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(REPO, "scripts"))
from siteparts import read_script_json, unpack  # noqa: E402

# fields the pages never read; proven unused by build/test_unused_fields.js and dropped from the parts
DROPPED = {"context ctx": ["pop"]}


def rows_of(cols):
    c = [unpack(s) for s in cols]
    return [[col[i] for col in c] for i in range(len(c[0]) if c else 0)]


def same(a, b, where, errors):
    """Deep equality with a readable first difference. ints and floats compare by value."""
    if isinstance(a, dict) and isinstance(b, dict):
        if set(a) != set(b):
            errors.append(f"{where}: keys differ (only old: {sorted(set(a) - set(b))[:5]}; only new: {sorted(set(b) - set(a))[:5]})")
            return
        for k in a:
            same(a[k], b[k], f"{where}.{k}", errors)
            if len(errors) > 20:
                return
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            errors.append(f"{where}: length {len(a)} vs {len(b)}")
            return
        for i, (x, y) in enumerate(zip(a, b)):
            same(x, y, f"{where}[{i}]", errors)
            if len(errors) > 20:
                return
    else:
        if isinstance(a, bool) or isinstance(b, bool) or (a is None) != (b is None):
            if a != b:
                errors.append(f"{where}: {a!r} vs {b!r}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            if not (a == b):
                errors.append(f"{where}: {a!r} vs {b!r}")
        elif a != b:
            errors.append(f"{where}: {a!r} vs {b!r}")


def rebuild_site(new):
    core = read_script_json(os.path.join(new, "data.js"))
    base = os.path.join(new, core["parts"]["base"])
    S = read_script_json(os.path.join(base, core["parts"]["schools"]))
    cov = {}
    for ceeb, cols in zip(S["ceebs"], S["data"]):
        for r in rows_of(cols):
            cov[(ceeb, r[0])] = r[1:]
    panel = {}
    for ci, fn in enumerate(core["parts"]["campus"]):
        C = read_script_json(os.path.join(base, fn))
        assert C["campus"] == ci
        for ceeb, cols in zip(C["ceebs"], C["data"]):
            rows = []
            for r in rows_of(cols):
                c = cov[(ceeb, r[0])]
                rows.append([r[0], r[1], r[2], r[3], c[0], c[1], c[2], c[3], c[4], c[5], c[6], r[4], r[5], r[6], c[7]])
            panel[f"{ci}|{ceeb}"] = rows
    O = read_script_json(os.path.join(base, core["parts"]["ucOutcomes"]))
    out = {k: v for k, v in core.items() if k != "parts"}
    out["panel"] = panel
    out["grad"] = {k: rows_of(v) for k, v in O["grad"].items()}
    out["gradC"] = {k: rows_of(v) for k, v in O["gradC"].items()}
    out["tests"] = O["tests"]
    return out


def rebuild_context(new):
    core = read_script_json(os.path.join(new, "context", "data_context.js"))
    base = os.path.join(new, "context", core["parts"]["base"])
    out = {k: v for k, v in core.items() if k != "parts"}
    ctx = {}
    for yr, fn in core["parts"]["ctx"].items():
        part = read_script_json(os.path.join(base, fn))
        assert str(part["year"]) == yr
        cols = [unpack(c) for c in part["cols"]]
        for i, ceeb in enumerate(part["ceebs"]):
            ctx.setdefault(ceeb, []).append([part["year"]] + [c[i] for c in cols])
    out["ctx"] = {ceeb: sorted(rows, key=lambda r: r[0]) for ceeb, rows in ctx.items()}
    sch = read_script_json(os.path.join(base, core["parts"]["sch"]))
    out["sch"] = {ceeb: rows_of(cols) for ceeb, cols in sch["sch"].items()}
    means = read_script_json(os.path.join(base, core["parts"]["means"]))
    out["means"] = means["means"]
    out["svars"] = sch["svars"]
    return out


def rebuild_trends(new):
    core = read_script_json(os.path.join(new, "trends", "data_trends.js"))
    base = os.path.join(new, "trends", core["parts"]["base"])
    out = {k: v for k, v in core.items() if k != "parts"}
    for name, fn in core["parts"]["files"].items():
        part = read_script_json(os.path.join(base, fn))
        if name in ("hs", "ccc"):
            out[name] = {"names": part["names"],
                         "series": {c: {k: rows_of(v) for k, v in s.items()} for c, s in part["series"].items()}}
        elif name == "gpa":
            out[name] = {"rates": {k: rows_of(v) for k, v in part["rates"].items()},
                         "cuts": {k: rows_of(v) for k, v in part["cuts"].items()}}
        else:
            out[name] = part
    return out


def rebuild_denied(new):
    core = read_script_json(os.path.join(new, "denied", "data_denied.js"))
    base = os.path.join(new, "denied", core["parts"]["base"])
    out = {k: v for k, v in core.items() if k != "parts"}
    n = len(core["schools"])
    by_campus = [[None] * len(core["campuses"]) for _ in range(n)]
    for ci, fn in enumerate(core["parts"]["campus"]):
        part = read_script_json(os.path.join(base, fn))
        assert part["campus"] == ci
        for si, cols in enumerate(part["series"]):
            by_campus[si][ci] = rows_of(cols) if cols else []
    by_school = [None] * n
    for fn in core["parts"]["schools"]:
        part = read_script_json(os.path.join(base, fn))
        for si, slots in zip(part["index"], part["series"]):
            by_school[si] = [rows_of(cols) if cols else [] for cols in slots]
    errors = []
    same(by_campus, by_school, "denied per-campus vs per-school parts", errors)
    if errors:
        raise SystemExit("denied parts disagree with each other: " + errors[0])
    out["series"] = by_campus
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", default=REPO)
    a = ap.parse_args()
    checks = [
        ("data.js (window.UCDATA)", os.path.join(a.old, "data.js"), rebuild_site),
        ("context/data_context.js (window.UCCTX)", os.path.join(a.old, "context", "data_context.js"), rebuild_context),
        ("trends/data_trends.js (window.TRENDS_DATA)", os.path.join(a.old, "trends", "data_trends.js"), rebuild_trends),
        ("denied/data_denied.js (window.UCDENIED)", os.path.join(a.old, "denied", "data_denied.js"), rebuild_denied),
    ]
    failed = False
    for label, old_path, rebuild in checks:
        old = read_script_json(old_path)
        new = rebuild(a.new)
        # fields proven unused and dropped from the new layer are removed from the old copy
        if label.startswith("context"):
            drop = [i for i, k in enumerate(old["cvars"]) if k in DROPPED["context ctx"]]
            old["cvars"] = [k for i, k in enumerate(old["cvars"]) if i not in drop]
            old["ctx"] = {ce: sorted([[v for i, v in enumerate(r) if i not in drop] for r in rows], key=lambda r: r[0]) for ce, rows in old["ctx"].items()}
        if label.startswith("trends"):
            old["meta"].pop("counts", None); new["meta"].pop("counts", None)   # a bookkeeping dict no page reads
        errors = []
        same(old, new, "", errors)
        counts = ""
        if "panel" in new:
            counts = f" ({len(new['panel'])} campus-school series, {sum(len(v) for v in new['panel'].values())} school-years)"
        if errors:
            failed = True
            print(f"FAIL  {label}{counts}")
            for e in errors[:10]:
                print("      " + e)
        else:
            print(f"ok    {label}{counts}: every value identical")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
