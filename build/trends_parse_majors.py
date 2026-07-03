#!/usr/bin/env python3
"""Aggregate IPEDS completions to campus x year x CIP-2 with URM counts.

Source: outcomes data/uc_ipeds_completions_package/
        uc_ipeds_completions_historical_long_2012_2024.csv  (~952k rows)
Filters: bachelor's degrees (AWLEVEL 05, award_level_type=detail), first major
only, sex total only, non-grand-total CIP, undergraduate campuses.
URM (basic) = Black + Hispanic/Latino + American Indian/Alaska Native +
Native Hawaiian/Pacific Islander (excludes two-or-more; federal race universe).

Output: data/trends/majors_cip2.csv
  campus, year (completions period start), cip2, cip2_title, total, urm, urm_share_pct

Counts are degrees conferred (completions), not graduation rates: a double
major appears under both majors' first-major rows only once (first major).
"""
import argparse, csv, os, json
from collections import defaultdict

URM_KEYS = {'black', 'hispanic', 'aian', 'nhpi',
            'black_non_hispanic', 'american_indian_alaska_native',
            'native_hawaiian_pacific_islander', 'hispanic_latino'}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    src = os.path.join(a.corpus, 'uc_ipeds_completions_package',
                       'uc_ipeds_completions_historical_long_2012_2024.csv')
    agg = defaultdict(lambda: [0, 0])
    titles = {}
    race_keys_seen = set()
    with open(src, encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            if (r['undergraduate_uc_campus'] != 'True' or r['AWLEVEL'].lstrip('0') != '5'
                    or r['award_level_type'] != 'detail' or r['MAJORNUM'] != '1'
                    or r['sex_key'] != 'total' or r['is_grand_total_cip'] == 'True'):
                continue
            rk = r['race_ethnicity_key']
            race_keys_seen.add(rk)
            n = int(float(r['completions'] or 0))
            if n == 0:
                continue
            yr = int(r['completions_period'].split('-')[0])
            k = (r['uc_campus'], yr, r['cip2'])
            titles[r['cip2']] = r['cip2_title']
            if rk == 'all_race_ethnicity':
                agg[k][0] += n
            elif rk in URM_KEYS:
                agg[k][1] += n
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, 'majors_cip2.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'year', 'cip2', 'cip2_title', 'total', 'urm', 'urm_share_pct'])
        for (c, y, cip), (tot, urm) in sorted(agg.items()):
            w.writerow([c, y, cip, titles[cip], tot, urm,
                        round(100.0 * urm / tot, 1) if tot else ''])
    qa = {'cells': len(agg), 'race_keys_seen': sorted(race_keys_seen),
          'years': sorted({k[1] for k in agg})}
    with open(os.path.join(a.out, 'majors_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1)
    print(json.dumps({'cells': len(agg), 'years': qa['years']}))
    print('race keys:', sorted(race_keys_seen))

if __name__ == '__main__':
    main()
