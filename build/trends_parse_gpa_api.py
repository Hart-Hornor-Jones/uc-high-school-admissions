#!/usr/bin/env python3
"""Parse the GPA-groups summary-API extraction into true band rates.

Source: outcomes data/ug_outcomes_gpa_groups_summary_api_full/vizql_long.csv
(VizQL logical-table extraction of the same 'Grad. rates by GPA groups'
dashboard the crosstabs came from — but with the full-precision band RATES
and inferred denominators the crosstab export rounds away or omits.
denominator = numerator / rate; the harvest's own check column shows
max |error| ~1e-12; 42 cells lack a denominator because their rate is 0.)

Grain: cohort 2010-2021 x campus (All + 9) x group (Pell / first-gen /
ethnicity / Overall — Overall covers ALL cohorts here, unlike the crosstab
export) x GPA band (systemwide terciles per cohort & entry type) x timing
window (FR: within-4 / 5th-only / 6th-only; TR: within-2 / 3rd-only /
4th-only).

Output: data/trends/gpa_rates.csv
  entry, campus, cohort, group_type, subgroup, band, band_lo, band_hi,
  denom, n_first, n_second, n_third, r_first_pct, r_second_pct, r_third_pct
(rates are percent with 2 decimals; *_second/_third are increment-only
windows — cumulative = sums, exact because the denominator is shared.
Immature cohorts carry real zeros in the later windows; the site gates
cumulative 5/6-yr measures to cohorts whose windows have closed.)
"""
import argparse, csv, os, re, json
from collections import defaultdict

GROUP = {
    'Pell Recipient': ('pell_status', 'pell'), 'Non-Pell Recipeint': ('pell_status', 'non_pell'),
    'Non-Pell Recipient': ('pell_status', 'non_pell'),
    'First-generation': ('first_gen_status', 'first_gen'),
    'Not first-generation': ('first_gen_status', 'not_first_gen'),
    'African American': ('ethnicity', 'black'), 'American Indian': ('ethnicity', 'aian'),
    'Asian': ('ethnicity', 'asian'), 'Chicano/Latino': ('ethnicity', 'hispanic_latino'),
    'White': ('ethnicity', 'white'), 'International': ('ethnicity', 'international'),
    'Overall': ('overall', 'overall'),
}
SLOT = {'4yr': 0, '5yr_only': 1, '6yr_only': 2, '2yr': 0, '3yr_only': 1, '4yr_only': 2}
BAND_RE = re.compile(r'([\d.]+)\s*[-–]\s*<?\s*([\d.]+)')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    src = os.path.join(a.corpus, 'ug_outcomes_gpa_groups_summary_api_full', 'vizql_long.csv')
    cells = {}
    fails = []
    for r in csv.DictReader(open(src, encoding='utf-8')):
        gv = r['group_value'].strip()
        if gv not in GROUP:
            fails.append(('unmapped group', gv))
            continue
        gtype, sub = GROUP[gv]
        entry = 'FR' if r['worksheet'].startswith('a.') else 'TR'
        mm = BAND_RE.search(r['gpa_range'])
        if not mm:
            fails.append(('bad range', r['gpa_range']))
            continue
        lo, hi = float(mm.group(1)), float(mm.group(2))
        slot = SLOT.get(r['measure_period'])
        if slot is None:
            continue
        key = (entry, r['campus'], int(r['cohort_year']), gtype, sub, lo, hi)
        cell = cells.setdefault(key, {'den': None, 'n': [None]*3, 'r': [None]*3})
        rate = r['graduation_rate_raw']
        num = r['numerator_count']
        den = r['cohort_denominator_inferred']
        if num != '':
            cell['n'][slot] = int(float(num))
        if rate != '':
            cell['r'][slot] = round(float(rate) * 100, 2)
        if den not in ('', None) and cell['den'] is None:
            cell['den'] = int(round(float(den)))
    # Synthesize 'Overall' (all entrants) for every cohort as the exact union of
    # the Pell partition: numerators and denominators sum; rate = sum/sum. The
    # dashboard's native Overall sheets (2019-20 only) reproduce these values.
    bases = {}
    for (entry, campus, cohort, gtype, sub, lo, hi), c in list(cells.items()):
        if gtype != 'pell_status':
            continue
        bases.setdefault((entry, campus, cohort, lo, hi), []).append(c)
    for (entry, campus, cohort, lo, hi), parts in bases.items():
        if len(parts) != 2:
            continue
        if any(x['den'] is None for x in parts):
            continue
        den = sum(x['den'] for x in parts)
        n = [None, None, None]
        r = [None, None, None]
        for slot in range(3):
            vals = [x['n'][slot] for x in parts]
            if all(v is not None for v in vals):
                n[slot] = sum(vals)
                r[slot] = round(100.0 * n[slot] / den, 2) if den else None
        key = (entry, campus, cohort, 'overall', 'overall', lo, hi)
        cells[key] = {'den': den, 'n': n, 'r': r}

    # Band index from the per-(entry,cohort) systemwide range triple (bands are
    # systemwide terciles: identical across campuses and groups), so sparse
    # cells with a missing band keep correct indices.
    triples = defaultdict(set)
    for (entry, campus, cohort, gtype, sub, lo, hi) in cells:
        triples[(entry, cohort)].add((lo, hi))
    bandof = {}
    for ec, ranges in triples.items():
        rs = sorted(ranges)
        if len(rs) != 3:
            fails.append(('range triple != 3', str(ec), len(rs)))
        for i, r in enumerate(rs, 1):
            bandof[(ec, r)] = i
    rows = []
    for key, c in cells.items():
        entry, campus, cohort, gtype, sub, lo, hi = key
        b = bandof.get(((entry, cohort), (lo, hi)))
        if b is None:
            fails.append(('unmapped band', str(key)))
            continue
        rows.append([entry, campus, cohort, gtype, sub, b, lo, hi,
                     c['den'] if c['den'] is not None else '']
                    + [x if x is not None else '' for x in c['n']]
                    + [x if x is not None else '' for x in c['r']])
    rows.sort(key=lambda r: (r[0], r[1], r[2], r[3], r[4], r[5]))
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'gpa_rates.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['entry', 'campus', 'cohort', 'group_type', 'subgroup', 'band', 'band_lo',
                    'band_hi', 'denom', 'n_first', 'n_second', 'n_third',
                    'r_first_pct', 'r_second_pct', 'r_third_pct'])
        w.writerows(rows)
    # QA: anchors + maturity + coverage
    qa = {'rows': len(rows), 'n_fails': len(fails), 'fails': fails[:10]}
    def find(e, c, y, g, s, b):
        for r in rows:
            if r[:6] == [e, c, y, g, s] + [b]:
                return r
    r = find('FR', 'All', 2010, 'pell_status', 'pell', 3)
    qa['anchor_all2010_pell_b3'] = r  # expect denom 4444, r_first 66.88
    mat = {}
    for e in ('FR', 'TR'):
        mat[e] = max((r[2] for r in rows if r[0] == e and r[11] not in ('', 0) ), default=None)
    qa['max_cohort_with_third_window'] = mat
    cov = sum(r[8] for r in rows if r[:5] == ['FR', 'All', 2019, 'pell_status', 'pell'] or
              r[:5] == ['FR', 'All', 2019, 'pell_status', 'non_pell'] if r[8] != '')
    qa['fr_all_2019_pell_partition_denom'] = cov
    with open(os.path.join(a.out, 'gpa_rates_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1, default=str)
    print(json.dumps(qa, default=str)[:600])

if __name__ == '__main__':
    main()
