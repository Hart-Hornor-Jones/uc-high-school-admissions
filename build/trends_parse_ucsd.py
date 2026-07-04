#!/usr/bin/env python3
"""Parse the UCSD retention/graduation full-grid harvest into a tidy CSV.

Source: outcomes data/ucsd_retention_full_grid/normalized_rates.csv —
VizQL extraction of UC San Diego's institutional-research dashboards
(First Year / Transfer x Graduation / Retention), on the grid
demographic-family x demographic-filter x UCSD school/division x cohort.
Rates are full precision (0-1); count = numerator; denominator inferred =
count / rate (cohort cell size). Cells under the dashboard's threshold are
flagged suppressed and dropped here.

Kept metrics (line worksheets; bar variants only where they add a horizon):
  FR: ret1, ret2, grad4, grad5, grad6      TR: ret1, grad2, grad3, grad4, grad5
The FR time-to-degree distribution worksheet ('bar chart grad rates (2)')
is not carried (increments of program-time buckets; see docs).

Output: data/trends/ucsd_rates.csv
  level, family, subgroup, school, cohort, measure, rate_pct, numer, denom
"""
import argparse, csv, os, json
from collections import Counter

FAM = {'Ethnic Broad': 'eth', 'First Generation': 'fg', 'Pell Recipient': 'pell'}
SUB = {
    'African American/Black': 'black', 'American Indian/Alaska Native': 'aian',
    'Asian/Asian American': 'asian', 'Chicanx/Latinx': 'hispanic_latino',
    'International': 'international', 'Native Hawaiian/Pacific Islander': 'nhpi',
    'Unknown/Decline to State': 'unknown', 'White/Caucasian': 'white',
    'First Generation': 'first_gen', 'Not First Generation': 'not_first_gen',
    'Pell Recipient': 'pell', 'Not Pell Recipient': 'non_pell',
}
# (tab, worksheet, metric) -> (level, measure, priority)  lower priority wins on dupes
MEAS = {
    ('First Year Graduation Rates', '4 yr rate', '4-year rate'): ('FR', 'grad4', 0),
    ('First Year Graduation Rates', '5 yr rate', '5-year rate'): ('FR', 'grad5', 0),
    ('First Year Graduation Rates', '6 yr rate', '6-year rate'): ('FR', 'grad6', 0),
    ('First Year Retention Rates', '1 Yr Retention', '1-year retention'): ('FR', 'ret1', 0),
    ('First Year Retention Rates', '2 Yr Retention (2)', '2-year retention'): ('FR', 'ret2', 0),
    ('Transfer Student Graduation Rates', '2- yr Grad', '2-year Grad'): ('TR', 'grad2', 0),
    ('Transfer Student Graduation Rates', '3 yr Grad', '3-year Grad'): ('TR', 'grad3', 0),
    ('Transfer Student Graduation Rates', '4 yr Grad', '4-year Grad'): ('TR', 'grad4', 0),
    ('Transfer Student Graduation Rates', 'Grad Rates Bar <10', '2-Year Rate'): ('TR', 'grad2', 1),
    ('Transfer Student Graduation Rates', 'Grad Rates Bar <10', '3-Year Rate'): ('TR', 'grad3', 1),
    ('Transfer Student Graduation Rates', 'Grad Rates Bar <10', '4-Year Rate'): ('TR', 'grad4', 1),
    ('Transfer Student Graduation Rates', 'Grad Rates Bar <10', '5-Year Rate'): ('TR', 'grad5', 1),
    ('Transfer Retention Rates', '1 yr Ret Bar <10', '1-year retention'): ('TR', 'ret1', 0),
}

def school_canon(s):
    s = s.strip()
    if 'Data Science' in s:
        return 'Halicioğlu Data Science Institute'
    if s.startswith('Herbert Wertheim'):
        return 'Public Health (Wertheim)'
    return s

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    src = os.path.join(a.corpus, 'ucsd_retention_full_grid', 'normalized_rates.csv')
    best = {}
    stats = Counter()
    for r in csv.DictReader(open(src, encoding='utf-8')):
        key3 = (r['tab'], r['worksheet'], r['metric'])
        if key3 not in MEAS:
            stats['skipped_metric'] += 1
            continue
        level, meas, prio = MEAS[key3]
        if r['suppressed_or_missing_rate'] != '0' or r['rate'] in ('', None):
            stats['suppressed_or_missing'] += 1
            continue
        fam = FAM.get(r['state_demographic_selection'])
        sub = SUB.get(r['state_demographic_filter'])
        if fam is None or sub is None:
            stats['dropped_filter'] += 1   # e.g. First Generation 'Null'
            continue
        school = school_canon(r['state_school'])
        try:
            cohort = int(r['cohort'])
        except ValueError:
            stats['bad_cohort'] += 1
            continue
        rate = float(r['rate'])
        numer = int(float(r['count'] or 0))
        den = r['cohort_denominator_inferred']
        den = int(round(float(den))) if den not in ('', None) else ''
        k = (level, fam, sub, school, cohort, meas)
        if k in best and best[k][0] <= prio:
            stats['dupe_lower_prio'] += 1
            continue
        best[k] = (prio, round(rate * 100, 2), numer, den)
    rows = [[*k, v[1], v[2], v[3]] for k, v in best.items()]
    rows.sort()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'ucsd_rates.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['level', 'family', 'subgroup', 'school', 'cohort', 'measure',
                    'rate_pct', 'numer', 'denom'])
        w.writerows(rows)
    qa = {'rows': len(rows), 'stats': dict(stats),
          'schools': sorted({r[3] for r in rows}),
          'measures': {'%s|%s' % k: v for k, v in Counter((r[0], r[5]) for r in rows).items()},
          'cohorts': [min(r[4] for r in rows), max(r[4] for r in rows)]}
    with open(os.path.join(a.out, 'ucsd_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1, default=str)
    print(json.dumps({k: qa[k] for k in ('rows', 'stats', 'cohorts')}, default=str))
    print('schools:', qa['schools'])
    print('measures:', sorted(qa['measures']))

if __name__ == '__main__':
    main()
