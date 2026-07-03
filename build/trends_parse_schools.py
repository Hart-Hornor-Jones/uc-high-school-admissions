#!/usr/bin/env python3
"""Prepare per-source-institution outcome series for the trends page.

High schools: reuse the repo's validated data/grad_rates_by_hs.csv
(campus x CEEB x entry year 1999-2024; cells masked below N=10 at source;
integer percents). Names/city/county come from the admissions source-school
dimension (same UC universe the outcomes table was matched against by
build/parse_grad_rates.py), with repo cross-section/crosswalk fallbacks.

Community colleges (transfer entrants): parse
outcomes data/.../ug_outcomes_transfer_grad_rates_by_ccc_internal_control/
crosstabs/<campus>/ccc-rate.csv (county, code, college, year, 1st yr,
2 yrs, 3 yrs, 4 yrs, Cohort Size).

Outputs: hs_series.csv, hs_names.csv, ccc_series.csv, ccc_names.csv
"""
import argparse, csv, os, re, json
from collections import defaultdict

CAMPUS_DIR = {'all': 'All', 'berkeley': 'Berkeley', 'davis': 'Davis', 'irvine': 'Irvine',
              'los-angeles': 'Los Angeles', 'merced': 'Merced', 'riverside': 'Riverside',
              'san-diego': 'San Diego', 'santa-barbara': 'Santa Barbara',
              'santa-cruz': 'Santa Cruz'}

def read_text(path):
    for enc in ('utf-8', 'utf-16', 'latin-1'):
        try:
            with open(path, encoding=enc) as f:
                t = f.read()
            if '\t' in t:
                return t
        except UnicodeError:
            continue
    raise IOError(path)

def num(s):
    s = (s or '').strip().replace(',', '').rstrip('%')
    if s in ('', '-'):
        return None
    try:
        return float(s)
    except ValueError:
        return None

def titlecase(s):
    small = {'of', 'the', 'and', 'at', 'in', 'for'}
    words = re.split(r'(\s+|-|/)', s.lower())
    out = []
    for i, w in enumerate(words):
        if re.match(r'^(\s+|-|/)$', w or ' '):
            out.append(w)
        elif w in small and i != 0:
            out.append(w)
        else:
            out.append(w.capitalize())
    return ''.join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repo', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions')
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=None)
    a = ap.parse_args()
    out = a.out or os.path.join(a.repo, 'data', 'trends')
    os.makedirs(out, exist_ok=True)
    qa = {}

    # names: primary = admissions school dimension
    names = {}
    dim = os.path.join(a.corpus, 'data', 'interim',
                       'admissions_source_school_consolidated_lean',
                       'admissions_freshman_school_dimension.csv')
    if os.path.exists(dim):
        for r in csv.DictReader(open(dim, encoding='utf-8')):
            c = (r.get('source_school_code_6') or '').strip()
            if c and c not in names and r.get('school_name'):
                names[c] = (titlecase(r['school_name'].strip()),
                            titlecase((r.get('city') or '').strip()),
                            titlecase((r.get('county_state_country') or '').strip()))
    for r in csv.DictReader(open(os.path.join(a.repo, 'data', 'cross_section_all9.csv'))):
        c = r['ceeb'].strip()
        if c and c not in names and r.get('school_name'):
            names[c] = (titlecase(r['school_name'].strip()), (r.get('city') or '').strip(),
                        (r.get('county') or '').strip())
    for r in csv.DictReader(open(os.path.join(a.repo, 'data', 'ceeb_cds_crosswalk.csv'))):
        c = r['ceeb'].strip()
        if c and c not in names:
            nm = (r.get('cde_name') or r.get('dv_name') or '').strip()
            if nm:
                names[c] = (titlecase(nm), '', '')

    # hs series (pass through; keep source masking)
    hs_rows, ceebs = [], set()
    for r in csv.DictReader(open(os.path.join(a.repo, 'data', 'grad_rates_by_hs.csv'))):
        hs_rows.append([r['campus'], r['ceeb'], int(r['entry_year']),
                        r['cohort_n'], r['ret1_pct'], r['grad4_pct'], r['grad5_pct'], r['grad6_pct']])
        ceebs.add(r['ceeb'])
    with open(os.path.join(out, 'hs_series.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'ceeb', 'entry_year', 'cohort_n', 'ret1_pct',
                    'grad4_pct', 'grad5_pct', 'grad6_pct'])
        w.writerows(sorted(hs_rows, key=lambda x: (x[0], x[1], x[2])))
    unmatched = sorted(c for c in ceebs if c not in names)
    with open(os.path.join(out, 'hs_names.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['ceeb', 'name', 'city', 'county'])
        for c in sorted(ceebs):
            nm, city, county = names.get(c, ('School (CEEB %s)' % c, '', ''))
            w.writerow([c, nm, city, county])
    qa['hs_rows'] = len(hs_rows)
    qa['hs_schools'] = len(ceebs)
    qa['hs_unnamed'] = len(unmatched)
    qa['hs_unnamed_sample'] = unmatched[:10]

    # ccc series
    base = os.path.join(a.corpus, 'data', 'raw', 'outcomes',
                        'ug_outcomes_transfer_grad_rates_by_ccc_internal_control', 'crosstabs')
    ccc_rows = []
    ccc_names = {}
    for d, campus in CAMPUS_DIR.items():
        path = os.path.join(base, d, 'ccc-rate.csv')
        if not os.path.exists(path):
            continue
        tab = [r.split('\t') for r in read_text(path).replace('\r', '').split('\n') if r.strip()]
        hdr = tab[0]
        tail = [h.strip() for h in hdr if h.strip()]
        for row in tab[1:]:
            vals = [x.strip() for x in row]
            yi = None
            for j, v in enumerate(vals[:6]):
                n = num(v)
                if n is not None and 1990 < n < 2030 and float(n).is_integer():
                    yi = j
                    break
            if yi is None or yi < 1:
                continue
            county = vals[0]
            code = vals[yi - 2] if yi >= 2 else ''
            college = vals[yi - 1]
            yr = int(num(vals[yi]))
            rest = vals[yi + 1:]
            vmap = dict(zip(tail, rest))
            n = num(vmap.get('Cohort Size'))
            rec = [campus, code or college, yr, int(n) if n is not None else '']
            for k in ('1st yr', '2 yrs', '3 yrs', '4 yrs'):
                v = num(vmap.get(k))
                rec.append(int(v) if v is not None else '')
            ccc_rows.append(rec)
            key = code or college
            if key not in ccc_names:
                ccc_names[key] = (titlecase(college), county.replace(' County', ''))
    with open(os.path.join(out, 'ccc_series.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'ccc_id', 'entry_year', 'cohort_n', 'ret1_pct',
                    'grad2_pct', 'grad3_pct', 'grad4_pct'])
        w.writerows(sorted(ccc_rows, key=lambda x: (x[0], str(x[1]), x[2])))
    with open(os.path.join(out, 'ccc_names.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['ccc_id', 'name', 'county'])
        for k, (nm, county) in sorted(ccc_names.items()):
            w.writerow([k, nm, county])
    qa['ccc_rows'] = len(ccc_rows)
    qa['ccc_colleges'] = len(ccc_names)
    with open(os.path.join(out, 'schools_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1)
    print(json.dumps(qa))

if __name__ == '__main__':
    main()
