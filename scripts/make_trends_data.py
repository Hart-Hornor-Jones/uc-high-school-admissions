#!/usr/bin/env python3
"""Bundle data/trends/*.csv into trends/data_trends.js (window.TRENDS_DATA) and
trends/data_parts/*.js (the by-institution, GPA-band and UCSD series, loaded on demand).

Everything the page shows is precomputed here; the page ships no raw data
beyond these aggregates. Values are already display-rounded by the parsers.

Run:  python3 scripts/make_trends_data.py [--generated YYYY-MM-DD]
"""
import csv, json, os, sys, datetime
from siteparts import pack, write_core, write_part

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(REPO, 'data', 'trends')
# the build date shown in the page footer: today, or --generated YYYY-MM-DD
GENERATED = sys.argv[sys.argv.index('--generated') + 1] if '--generated' in sys.argv else datetime.date.today().isoformat()

def rd(name):
    with open(os.path.join(D, name), newline='', encoding='utf-8') as fh:
        return list(csv.DictReader(fh))

def fnum(v):
    if v is None or v == '':
        return None
    x = float(v)
    return int(x) if x == int(x) else x

out = {}

# ---- systemwide (UC IC) ----
sys_series = {}
for r in rd('sys_rates.csv'):
    key = '|'.join([r['level'], r['slice'], r['eth'], r['pell'], r['fg']])
    m = sys_series.setdefault(key, {})
    m.setdefault(r['measure'], []).append([int(r['cohort']), fnum(r['value']), fnum(r['n'])])
for k in sys_series:
    for meas in sys_series[k]:
        sys_series[k][meas].sort()

# synthesize all-ethnicity Pell / first-gen aggregates from the cross slices.
# Rate cells are graduate(or retained) share x cohort N, so the N-weighted mean
# over the full ethnicity partition equals the true combined rate (cells are
# published to 0.1pp; aggregation error is negligible). Only rate measures with
# per-cell Ns are aggregated; TTD/GPA means are left to the ethnicity view.
RATE_MEASURES = {'ret1','grad2','grad3','grad4','grad5','grad6','grad5p','grad7p'}
def synth(level, slice_, field_vals, out_key_tail):
    eths = ['aian','asian_pi','black','hispanic_latino','international','unknown','white']
    for fv in field_vals:
        agg = {}
        complete = {}
        for e in eths:
            k = '|'.join([level, slice_, e] + fv)
            src = sys_series.get(k)
            if not src:
                continue
            for meas, arr in src.items():
                if meas not in RATE_MEASURES:
                    continue
                for yr, v, n in arr:
                    if v is None or not n:
                        continue
                    g, den, cnt = agg.get((meas, yr), (0.0, 0, 0))
                    agg[(meas, yr)] = (g + v * n / 100.0, den + n, cnt + 1)
        out_series = {}
        for (meas, yr), (g, den, cnt) in agg.items():
            if den < 1 or cnt < 5:   # require most ethnicities present
                continue
            out_series.setdefault(meas, []).append([yr, round(100.0 * g / den, 1), den])
        for meas in out_series:
            out_series[meas].sort()
        if out_series:
            sys_series['|'.join([level, 'agg'] + out_key_tail(fv))] = out_series

for level in ('FR', 'TR'):
    synth(level, 'eth_x_pell', [['pell', 'all'], ['non_pell', 'all']],
          lambda fv: ['all', fv[0], 'all'])
    synth(level, 'eth_x_fg', [['all', 'first_gen'], ['all', 'not_first_gen']],
          lambda fv: ['all', 'all', fv[1]])

out['sys'] = sys_series

# ---- federal campus panel ----
panel, stats = {}, {}
for r in rd('fed_campus_panel.csv'):
    yr = int(r['year'])
    if r['group'] == '__campus__':
        stats.setdefault(r['campus'], []).append(
            [yr, fnum(r['ret_ft4_pct']), fnum(r['pctpell']), fnum(r['ftftpctpell']), fnum(r['ugds'])])
    else:
        if r['c150_pct'] == '' and r['d150'] == '':
            continue
        panel.setdefault(r['campus'] + '|' + r['group'], []).append(
            [yr, fnum(r['c150_pct']), fnum(r['d150'])])
for d in (panel, stats):
    for k in d:
        d[k].sort()
money = {}
for r in rd('fed_money.csv'):
    money.setdefault(r['campus'], {})[r['metric'] + '|' + r['subgroup']] = \
        [fnum(r['value']), fnum(r['n'])]
fg = {}
for r in rd('fed_firstgen_curves.csv'):
    fg.setdefault(r['campus'] + '|' + r['group'], {}).setdefault(r['outcome'], []).append(
        [int(r['years_after_entry']), fnum(r['rate_pct']), fnum(r['cohort_n'])])
for k in fg:
    for oc in fg[k]:
        fg[k][oc].sort()
out['fed'] = {'panel': panel, 'stats': stats, 'money': money, 'fg': fg}

# ---- high schools ----
names, series = {}, {}
for r in rd('hs_names.csv'):
    names[r['ceeb']] = [r['name'], r['city'], r['county']]
for r in rd('hs_series.csv'):
    series.setdefault(r['campus'], {}).setdefault(r['ceeb'], []).append(
        [int(r['entry_year']), fnum(r['cohort_n']), fnum(r['ret1_pct']),
         fnum(r['grad4_pct']), fnum(r['grad5_pct']), fnum(r['grad6_pct'])])
for c in series:
    for s in series[c]:
        series[c][s].sort()
out['hs'] = {'names': names, 'series': series}

# ---- community colleges ----
cnames, cseries = {}, {}
for r in rd('ccc_names.csv'):
    cnames[r['ccc_id']] = [r['name'], r['county']]
for r in rd('ccc_series.csv'):
    cseries.setdefault(r['campus'], {}).setdefault(r['ccc_id'], []).append(
        [int(r['entry_year']), fnum(r['cohort_n']), fnum(r['ret1_pct']),
         fnum(r['grad2_pct']), fnum(r['grad3_pct']), fnum(r['grad4_pct'])])
for c in cseries:
    for s in cseries[c]:
        cseries[c][s].sort()
out['ccc'] = {'names': cnames, 'series': cseries}

# ---- GPA bands: true rates from the summary-API harvest ----
grates, gcuts = {}, {}
for r in rd('gpa_rates.csv'):
    key = '|'.join([r['entry'], r['campus'], r['group_type'], r['subgroup']])
    grates.setdefault(key, []).append(
        [int(r['cohort']), int(r['band']), fnum(r['band_lo']), fnum(r['band_hi']),
         fnum(r['denom']), fnum(r['n_first']), fnum(r['n_second']), fnum(r['n_third']),
         fnum(r['r_first_pct']), fnum(r['r_second_pct']), fnum(r['r_third_pct'])])
for k in grates:
    grates[k].sort()
for r in rd('gpa_cutpoints.csv'):
    gcuts.setdefault(r['entry'] + '|' + r['campus'], []).append(
        [int(r['cohort']), fnum(r['q_lo']), fnum(r['q1_hi']), fnum(r['q2_hi']), fnum(r['q_hi'])])
for k in gcuts:
    gcuts[k].sort()
out['gpa'] = {'rates': grates, 'cuts': gcuts}

# ---- UCSD deep dive ----
usd = {}
uschools = set()
for r in rd('ucsd_rates.csv'):
    key = '|'.join([r['level'], r['family'], r['subgroup'], r['school']])
    usd.setdefault(key, {}).setdefault(r['measure'], []).append(
        [int(r['cohort']), fnum(r['rate_pct']), fnum(r['denom'])])
    uschools.add(r['school'])
for k in usd:
    for mm in usd[k]:
        usd[k][mm].sort()
out['ucsd'] = {'schools': sorted(uschools), 'series': usd}

# ---- UC Berkeley deep dive ----
ucb = {}
for r in rd('ucb_rates.csv'):
    key = '|'.join([r['level'], r['dimension'], r['subgroup']])
    ucb.setdefault(key, {}).setdefault(r['measure'], []).append(
        [int(r['cohort']), fnum(r['rate_pct']), fnum(r['denom'])])
for k in ucb:
    for mm in ucb[k]:
        ucb[k][mm].sort()
out['ucb'] = {'series': ucb}

# ---- majors ----
titles, mseries = {}, {}
for r in rd('majors_cip2.csv'):
    titles[r['cip2']] = r['cip2_title']
    mseries.setdefault(r['campus'] + '|' + r['cip2'], []).append(
        [int(r['year']), fnum(r['total']), fnum(r['urm'])])
for k in mseries:
    mseries[k].sort()
out['majors'] = {'titles': titles, 'series': mseries}

out['meta'] = {
    'built': GENERATED,
    'counts': {k: (len(v) if isinstance(v, dict) else None) for k, v in out.items()},
    'sources': {
        'uc_ic': 'UC Information Center UG Outcomes & Admissions-by-source-school dashboards (harvested June 2026)',
        'scorecard': 'College Scorecard institution files, June 10 2026 vintage',
        'ipeds': 'IPEDS Completions C2012-C2024 (provisional 2023-24)',
        'ucsd': 'UC San Diego Institutional Research retention/graduation dashboards (harvested June 2026)',
        'ucb': 'UC Berkeley OPAP Disaggregated Grad Rates dashboard + Our Berkeley data downloads (harvested July 2026)',
    },
}

# ---- write: core + parts ----
# The page opens on the systemwide view; the by-institution series (hs, ccc), the GPA bands and
# the UCSD deep dive are each fetched by ../ucparts.js when their mode is chosen. Series rows
# inside parts travel as packed columns (see scripts/siteparts.py).
GEN = 'scripts/make_trends_data.py'
PARTS_DIR = os.path.join(REPO, 'trends', 'data_parts')
def packed_series(series, ncols):
    return {c: {k: pack_rows(v, ncols) for k, v in s.items()} for c, s in series.items()}
def pack_rows(rows, ncols):
    return [pack([r[i] for r in rows]) for i in range(ncols)]
parts = {
    'hs':   {'names': out['hs']['names'],  'series': packed_series(out['hs']['series'], 6)},
    'ccc':  {'names': out['ccc']['names'], 'series': packed_series(out['ccc']['series'], 6)},
    'gpa':  {'rates': {k: pack_rows(v, 11) for k, v in out['gpa']['rates'].items()},
             'cuts':  {k: pack_rows(v, 5) for k, v in out['gpa']['cuts'].items()}},
    'ucsd': out['ucsd'],
}
core = {k: v for k, v in out.items() if k not in parts}
core['parts'] = {'base': 'data_parts/', 'files': {k: k + '.js' for k in parts}}
sizes = {k: write_part(os.path.join(PARTS_DIR, k + '.js'), 'trends:' + k, v, GEN) for k, v in parts.items()}
dst = os.path.join(REPO, 'trends', 'data_trends.js')
core_size = write_core(dst, 'TRENDS_DATA', core, GEN)
print('wrote', dst, core_size, 'bytes; parts:', ', '.join(f'{k} {v} bytes' for k, v in sizes.items()))
for k, v in out.items():
    if isinstance(v, dict):
        print(' ', k, {kk: len(vv) if isinstance(vv, (dict, list)) else '' for kk, vv in list(v.items())[:6] if isinstance(vv, (dict, list))})
