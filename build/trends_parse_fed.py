#!/usr/bin/env python3
"""Parse the curated Scorecard/IPEDS packages into tidy CSVs for the trends page.

Inputs (inside the outcomes-data corpus):
  uc_scorecard_package/uc_historical_completion_panel.csv
  uc_scorecard_package/uc_campus_outcomes_earnings_debt_repayment.csv
  uc_scorecard_package/uc_firstgen_titleiv_outcomes_long.csv

Outputs (repo data/trends/):
  fed_campus_panel.csv   campus x year x group -> c150 (%), d150, ret_ft4, pctpell
  fed_money.csv          campus x metric x subgroup -> value, n   (single vintage)
  fed_firstgen_curves.csv campus x group x years_after_entry x outcome -> rate, n

Universe: federal (IPEDS FTFT cohorts / Scorecard NSLDS Title-IV). Never mixed
with UC IC series in one chart. C150_4 published in data year Y reflects a
cohort entering roughly Y-6; we keep the data year and note the lag.
"""
import argparse, csv, os, json

RACE = [('overall',''), ('white','_WHITE'), ('black','_BLACK'), ('hispanic_latino','_HISP'),
        ('asian','_ASIAN'), ('aian','_AIAN'), ('nhpi','_NHPI'), ('two_or_more','_2MOR'),
        ('international','_NRA'), ('unknown','_UNKN'), ('urm_basic','_URM_BASIC_DERIVED'),
        ('pell','_PELL'), ('loan_no_pell','_LOANNOPELL'), ('no_loan_no_pell','_NOLOANNOPELL')]

def f(v):
    v = (v or '').strip()
    if v in ('', 'NULL', 'PrivacySuppressed', 'PS', 'None'):
        return None
    try:
        return float(v)
    except ValueError:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=r'C:\Users\harth\svetlana\outcomes data')
    ap.add_argument('--out', default=r'C:\Users\harth\svetlana\Svetlana\uc-merit-admissions\data\trends')
    a = ap.parse_args()
    sc = os.path.join(a.corpus, 'uc_scorecard_package')
    os.makedirs(a.out, exist_ok=True)
    qa = {}

    # --- campus historical panel ---
    rows = []
    for r in csv.DictReader(open(os.path.join(sc, 'uc_historical_completion_panel.csv'))):
        if r.get('undergraduate_uc_campus', '') != 'True':
            continue
        campus = r['uc_campus']
        year = int(r['academic_year'].split('-')[0])
        for key, suf in RACE:
            c = f(r.get('C150_4' + suf))
            d = f(r.get('D150_4' + suf))
            if c is None and d is None:
                continue
            rows.append([campus, year, key,
                         round(c * 100, 1) if c is not None else '',
                         int(d) if d is not None else ''])
        ret = f(r.get('RET_FT4'))
        pp = f(r.get('PCTPELL'))
        fp = f(r.get('FTFTPCTPELL'))
        ug = f(r.get('UGDS'))
        if any(v is not None for v in (ret, pp, fp, ug)):
            rows.append([campus, year, '__campus__',
                         '', ''])
            rows[-1] += [round(ret * 100, 1) if ret is not None else '',
                         round(pp * 100, 1) if pp is not None else '',
                         round(fp * 100, 1) if fp is not None else '',
                         int(ug) if ug is not None else '']
    # normalize width
    with open(os.path.join(a.out, 'fed_campus_panel.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'year', 'group', 'c150_pct', 'd150', 'ret_ft4_pct', 'pctpell', 'ftftpctpell', 'ugds'])
        for r in rows:
            w.writerow(r + [''] * (9 - len(r)))
    qa['fed_campus_panel_rows'] = len(rows)
    qa['berkeley_latest_c150'] = [r for r in rows if r[0] == 'Berkeley' and r[2] == 'overall'][-3:]

    # --- money (single vintage) ---
    money = []
    for r in csv.DictReader(open(os.path.join(sc, 'uc_campus_outcomes_earnings_debt_repayment.csv'))):
        if r.get('undergraduate_uc_campus', '') != 'True':
            continue
        c = r['uc_campus']
        for horizon in ('P6', 'P8', 'P10'):
            money.append([c, 'earnings_' + horizon.lower(), 'overall',
                          f(r.get('MD_EARN_WNE_' + horizon)), f(r.get('COUNT_WNE_' + horizon))])
            for inc, lab in (('INC1', 'inc_low'), ('INC2', 'inc_mid'), ('INC3', 'inc_high')):
                money.append([c, 'earnings_' + horizon.lower(), lab,
                              f(r.get('MD_EARN_WNE_%s_%s' % (inc, horizon))),
                              f(r.get('COUNT_WNE_%s_%s' % (inc, horizon)))])
        for var, metric, sub in (
                ('GRAD_DEBT_MDN', 'debt_grad', 'overall'),
                ('PELL_DEBT_MDN', 'debt_grad', 'pell'), ('NOPELL_DEBT_MDN', 'debt_grad', 'non_pell'),
                ('LO_INC_DEBT_MDN', 'debt_grad', 'inc_low'), ('MD_INC_DEBT_MDN', 'debt_grad', 'inc_mid'),
                ('HI_INC_DEBT_MDN', 'debt_grad', 'inc_high'),
                ('FIRSTGEN_DEBT_MDN', 'debt_grad', 'first_gen'),
                ('NOTFIRSTGEN_DEBT_MDN', 'debt_grad', 'not_first_gen')):
            nvar = var.replace('_MDN', '_N')
            money.append([c, metric, sub, f(r.get(var)), f(r.get(nvar))])
    money = [m for m in money if m[3] is not None]
    with open(os.path.join(a.out, 'fed_money.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'metric', 'subgroup', 'value', 'n'])
        for m in money:
            w.writerow([m[0], m[1], m[2], int(m[3]), int(m[4]) if m[4] else ''])
    qa['fed_money_rows'] = len(money)

    # --- first-gen NSLDS curves ---
    keep_outcomes = {'comp_orig': 'completed_here', 'comp_4yr_trans': 'completed_via_4yr_transfer',
                     'comp_2yr_trans': 'completed_via_2yr_transfer', 'wdraw_orig': 'withdrew',
                     'enrl_orig': 'still_enrolled'}
    fg = []
    for r in csv.DictReader(open(os.path.join(sc, 'uc_firstgen_titleiv_outcomes_long.csv'))):
        if r.get('undergraduate_uc_campus', '') != 'True':
            continue
        oc = r['outcome']
        if oc not in keep_outcomes:
            continue
        v = f(r['rate'])
        if v is None:
            continue
        fg.append([r['uc_campus'], r['generation_group'], int(r['years_after_entry']),
                   oc, round(v * 100, 1), int(float(r['cohort_count'] or 0))])
    with open(os.path.join(a.out, 'fed_firstgen_curves.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['campus', 'group', 'years_after_entry', 'outcome', 'rate_pct', 'cohort_n'])
        w.writerows(sorted(fg))
    qa['fed_firstgen_rows'] = len(fg)

    # majors moved to build/trends_parse_majors.py (full IPEDS long file;
    # the package's pre-aggregated summaries cover 2022-24 only)

    with open(os.path.join(a.out, 'fed_qa.json'), 'w') as fh:
        json.dump(qa, fh, indent=1, default=str)
    print(json.dumps({k: (v if isinstance(v, int) else '…') for k, v in qa.items()}))
    print('berkeley_latest_c150', qa['berkeley_latest_c150'])

if __name__ == '__main__':
    main()
