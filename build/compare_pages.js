// compare_pages.js - the old (single-script) pages and the new (data-parts) pages must draw the
// same thing. This drives the same sequence of control selections on both copies of each of the
// five pages, headless, and asserts that
//   * the text content of every SVG on the page is identical (axis ticks, labels, chart text),
//   * every Pearson r readout and statistic the page prints is identical, and
//   * (strict) the full SVG markup is identical, element for element and attribute for attribute.
// It then opens the new pages from file:// to show that direct opening still works.
//
// usage:
//   node build/compare_pages.js --old <checkout of the pre-split site> --new <repo root>
//                               [--d3 <path to d3.min.js>] [--report <out.md>]
//
// The old checkout is any directory holding the previous index.html, data.js and companion
// pages (for example `git worktree add ../old main`). --d3 serves a local copy of d3 7.8.5 in
// place of the cdnjs response where that host is unreachable.
//
// Requires: node 18+, playwright with its Chromium. No other dependencies.
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');
const { pathToFileURL } = require('url');

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.csv': 'text/csv; charset=utf-8' };

function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) {
    const k = a[i];
    if (k === '--old') o.old = a[++i];
    else if (k === '--new') o.new = a[++i];
    else if (k === '--d3') o.d3 = a[++i];
    else if (k === '--report') o.report = a[++i];
    else throw new Error('unknown argument ' + k);
  }
  if (!o.old || !o.new) throw new Error('--old and --new are required');
  return o;
}

function serve(root) {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p.endsWith('/')) p += 'index.html';
      const file = path.join(root, p);
      if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); res.end(); return; }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
      fs.createReadStream(file).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, base: 'http://127.0.0.1:' + server.address().port + '/' }));
  });
}

// ---- driving helpers ----
// Every control action first waits for the page to settle (a part the previous action asked for
// may still be arriving), as a reader would; on the old pages there is never anything pending.
const idle = pg => pg.evaluate(() => (window.UCPARTS && window.UCPARTS.whenIdle) ? window.UCPARTS.whenIdle() : null);
const sel = async (pg, s, v) => { await idle(pg); await pg.selectOption(s, v); };
const click = async (pg, s) => { await idle(pg); await pg.click(s); };
const check = async (pg, s, on) => { await idle(pg); if (on === false) await pg.uncheck(s); else await pg.check(s); };
const clickFirst = async (pg, s) => { await idle(pg); await pg.$eval(s, el => el.dispatchEvent(new MouseEvent('click', { bubbles: true }))); };
const setSlider = async (pg, s, v) => { await idle(pg); await pg.$eval(s, (el, v) => { el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }, v); };
const search = async (pg, s, text) => { await idle(pg); await pg.$eval(s, (el, t) => { el.value = t; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); }, text); };
const optionValue = (pg, s, i) => pg.evaluate(([s, i]) => document.querySelectorAll(s)[i].value, [s, i]);

// What is compared after each state: the text of every SVG, the readouts (r values, statistics,
// titles, tables, profile cards) and the full SVG markup.
const READOUTS = {
  '':         ['plotTitle', 'plotSub', 'bigr', 'interp', 'statCampus', 'sNshown', 'kOverall', 'sOverall', 'sPooled', 'sGap', 'denoms', 'sparkLbl', 'legend', 'profile', 'profNote'],
  'context/': ['plotTitle', 'plotSub', 'statHead', 'statsBody', 'legend', 'profile'],
  'trends/':  ['plotTitle', 'plotSub', 'maskNote', 'seriesnote', 'gatenote', 'chips', 'cutnote', 'universeBadge'],
  'denied/':  ['titleT', 'lT', 'tblT', 'titleW', 'wallModeNote', 'lW', 'titleF', 'lF', 'fMovers', 'fZoomNote', 'scopeNote'],
  'history/': ['titleArc', 'sumArc', 'tblArc', 'lArc', 'qArc', 'titleAP', 'lAP', 'apN', 'dApR', 'wN', 'wMean', 'wPos', 'wR', 'dSplit', 'dFlatN', 'dFlatShare', 'dFlatSlope', 'agDiff', 'agPairs', 'gridNote', 'rsVol', 'lVol', 'lWedge', 'lRulers'],
};
async function capture(pg, page) {
  return pg.evaluate(ids => {
    const svgs = [...document.querySelectorAll('svg')].filter(s => s.closest('#exportMenu') == null);
    const text = svgs.map(s => s.textContent).join('\u0001');
    const markup = svgs.map(s => s.outerHTML).join('\u0001');
    const readouts = ids.map(id => { const el = document.getElementById(id); return id + '=' + (el ? el.textContent.replace(/\s+/g, ' ').trim() : '(absent)'); }).join('\u0001');
    // every signed two-decimal number in the readouts: the Pearson r values and the gaps
    const rs = (readouts.match(/[+−-]\d\.\d\d\b/g) || []).join(' ');
    const shapes = document.querySelectorAll('svg circle, svg path, svg rect, svg line').length;
    return { text, markup, readouts, rs, shapes };
  }, READOUTS[page]);
}

// The control sequence per page. Each state is [name, async pg => ...]; the first is the page as
// opened. Campus and period changes appear on every page that has them.
const STATES = {
  '': [
    ['as opened (Berkeley, 2023-2025, admit rate vs CAASPP)', async () => {}],
    ['campus: San Diego', async pg => sel(pg, '#campus', '6')],
    ['period: 2016-2019', async pg => sel(pg, '#period', 'p1619')],
    ['Y: admits per graduate; X: UPP', async pg => { await sel(pg, '#metricB', 'adm_per_grad'); await sel(pg, '#metricA', 'upp'); }],
    ['Y: 6-yr graduation at this campus (UC outcome tables)', async pg => sel(pg, '#metricB', 'grad6_camp')],
    ['X: UC-wide 6-yr grad of prior cohorts; color: distance', async pg => { await sel(pg, '#metricA', 'grad6_prior'); await sel(pg, '#colorby', 'dist'); }],
    ['min applicants 80; outliers hidden; dots by size', async pg => { await setSlider(pg, '#minapps', 80); await check(pg, '#dropout'); await check(pg, '#dotvary'); }],
    ['period: 2024; campus: Merced', async pg => { await sel(pg, '#period', 'y2024'); await sel(pg, '#campus', '4'); }],
    ['strip view, applicant GPA', async pg => { await click(pg, '#view button[data-v="strip"]'); await sel(pg, '#metricA', 'app_gpa'); }],
    ['strip view, UC-wide retention', async pg => sel(pg, '#metricA', 'ret1_same')],
    ['scatter again (admit rate vs CAASPP), Riverside 2023-2025; click a school (profile card)', async pg => { await click(pg, '#view button[data-v="scatter"]'); await sel(pg, '#metricA', 'avg'); await sel(pg, '#metricB', 'admit_rate'); await sel(pg, '#campus', '5'); await sel(pg, '#period', 'p2325'); await check(pg, '#dropout', false); await clickFirst(pg, '#chart circle'); }],
    ['search: Lowell High School (profile card)', async pg => search(pg, '#search', 'LOWELL HIGH SCHOOL')],
  ],
  'context/': [
    ['as opened (conditioning scatter, SES)', async () => {}],
    ['campus: Los Angeles; context: UPP', async pg => { await sel(pg, '#campus', '3'); await sel(pg, '#ctxMetric', 'upp'); }],
    ['context: % SED (grade-11 composition part); second: median income', async pg => { await sel(pg, '#ctxMetric', 'sed'); await sel(pg, '#ctx2Metric', 'inc'); }],
    ['achievement: ELA mean score; outcome: applicant GPA', async pg => { await sel(pg, '#achMetric', 'ela_mean'); await sel(pg, '#outMetric', 'app_gpa'); }],
    ['context: application rate to the other 8 (every campus)', async pg => { await sel(pg, '#ctxMetric', 'app_rate_oth'); await sel(pg, '#ctx2Metric', 'none'); }],
    ['local-correlation curve, all campuses, period 2019', async pg => { await click(pg, '#view button[data-v="curve"]'); await check(pg, '#allcamp'); await sel(pg, '#period', 'y2019'); }],
    ['twin schools, ZCTA match, 2023-2025', async pg => { await click(pg, '#view button[data-v="twins"]'); await sel(pg, '#matchMode', 'zcta'); await sel(pg, '#period', 'p2325'); await sel(pg, '#ctxMetric', 'ses'); await sel(pg, '#achMetric', 'avg'); }],
    ['variance decomposition (all nine campuses)', async pg => click(pg, '#view button[data-v="decomp"]')],
    ['conditioning scatter, San Diego; click a school (profile card)', async pg => { await click(pg, '#view button[data-v="cond"]'); await sel(pg, '#campus', '6'); await sel(pg, '#outMetric', 'admit_rate'); await clickFirst(pg, '#chart circle'); }],
  ],
  'trends/': [
    ['as opened (systemwide, ethnicity, 6-yr graduation)', async () => {}],
    ['split by Pell; transfer level', async pg => { await sel(pg, '#horizon', 'pell'); await click(pg, '#level button[data-v="TR"]'); }],
    ['campuses (federal panel)', async pg => sel(pg, '#mode', 'fed')],
    ['high schools (part); campus: San Diego', async pg => { await sel(pg, '#mode', 'hs'); await sel(pg, '#campus', 'San Diego'); }],
    ['community colleges (part); campus: Davis; 2-yr measure', async pg => { await sel(pg, '#mode', 'ccc'); await sel(pg, '#campus', 'Davis'); await sel(pg, '#measure', 'grad2'); }],
    ['GPA bands (part), Berkeley', async pg => { await sel(pg, '#mode', 'gpa'); await sel(pg, '#campus', 'Berkeley'); }],
    ['UC San Diego deep dive (part)', async pg => sel(pg, '#mode', 'ucsd')],
    ['UC Berkeley deep dive; majors; earnings & debt', async pg => { await sel(pg, '#mode', 'ucb'); await sel(pg, '#mode', 'majors'); await sel(pg, '#mode', 'money'); }],
    ['first-generation (federal), campus Irvine', async pg => { await sel(pg, '#mode', 'fgfed'); await sel(pg, '#campus', 'Irvine'); }],
  ],
  'denied/': [
    ['as opened (all schools, Berkeley)', async () => {}],
    ['campus: San Diego (chip)', async pg => click(pg, '#campusChips button:nth-child(4)')],
    ['school: the 100th in the list (bucket part)', async pg => search(pg, '#search', await optionValue(pg, '#schoollist option', 100))],
    ['wall in relative mode; field years 2000/2010/2020', async pg => { await click(pg, '#wallMode button[data-mode="rel"]'); await sel(pg, '#fy0', '2000'); await sel(pg, '#fy1', '2010'); await sel(pg, '#fy2', '2020'); }],
    ['campus: Merced (chip) for the same school', async pg => click(pg, '#campusChips button:nth-child(10)')],
    ['school: the 1500th in the list', async pg => search(pg, '#search', await optionValue(pg, '#schoollist option', 1500))],
    ['back to all schools, Universitywide', async pg => { await click(pg, '#clearSchool'); await click(pg, '#campusChips button:nth-child(1)'); }],
  ],
  'history/': [
    ['as opened (Berkeley)', async () => {}],
    ['campus: San Diego (chip)', async pg => click(pg, '#campusChips button:nth-child(3)')],
    ['campus: Merced; AP mode: share 3+', async pg => { await click(pg, '#campusChips button:nth-child(10)'); await click(pg, '#apMode button:nth-child(2)'); }],
    ['campus: Universitywide', async pg => click(pg, '#campusChips button:nth-child(1)')],
  ],
};
const PAGE_LABEL = { '': 'root (index.html)', 'context/': 'context/', 'trends/': 'trends/', 'denied/': 'denied/', 'history/': 'history/' };

async function drive(browser, base, page, d3) {
  const pg = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const errors = [];
  pg.on('pageerror', e => errors.push(String(e.message)));
  pg.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  if (d3) await pg.route(/d3(\.min)?\.js$/, r => r.fulfill({ path: d3, contentType: 'application/javascript' }));
  await pg.goto(base + page, { waitUntil: 'load' });
  await idle(pg);
  const snaps = [];
  for (const [name, act] of STATES[page]) {
    let actErr = null;
    try { await act(pg); } catch (e) { actErr = String(e.message).split('\n')[0]; }
    await idle(pg);
    await pg.waitForTimeout(60);              // debounced handlers (resize, input) settle
    const snap = await capture(pg, page);
    snap.name = name; snap.actErr = actErr;
    snaps.push(snap);
  }
  await pg.close();
  return { snaps, errors };
}

async function fileCheck(browser, root, d3) {
  const out = [];
  for (const page of Object.keys(STATES)) {
    const pg = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    pg.on('pageerror', e => errors.push(String(e.message)));
    if (d3) await pg.route(/d3(\.min)?\.js$/, r => r.fulfill({ path: d3, contentType: 'application/javascript' }));
    await pg.goto(pathToFileURL(path.join(root, page, 'index.html')).href, { waitUntil: 'load' });
    await idle(pg);
    const shapes = await pg.evaluate(() => document.querySelectorAll('svg circle, svg path, svg rect, svg line').length);
    out.push({ page: PAGE_LABEL[page], shapes, errors });
    await pg.close();
  }
  return out;
}

async function main() {
  const o = args();
  const { chromium } = require('playwright');
  const oldRoot = path.resolve(o.old), newRoot = path.resolve(o.new);
  const [so, sn] = [await serve(oldRoot), await serve(newRoot)];
  const browser = await chromium.launch();
  const lines = [], md = [];
  let states = 0, failures = 0;
  md.push('| Page | State | SVG text | r readouts | readouts | SVG markup | shapes |', '|---|---|:-:|:-:|:-:|:-:|--:|');
  for (const page of Object.keys(STATES)) {
    const [a, b] = await Promise.all([drive(browser, so.base, page, o.d3), drive(browser, sn.base, page, o.d3)]);
    for (let i = 0; i < a.snaps.length; i++) {
      const x = a.snaps[i], y = b.snaps[i]; states++;
      const same = { text: x.text === y.text, rs: x.rs === y.rs, readouts: x.readouts === y.readouts, markup: x.markup === y.markup };
      const ok = same.text && same.rs && same.readouts && same.markup && !x.actErr && !y.actErr;
      if (!ok) failures++;
      const mark = v => v ? 'same' : '**DIFF**';
      md.push(`| ${PAGE_LABEL[page]} | ${x.name}${x.actErr || y.actErr ? ' (control error: ' + (x.actErr || y.actErr) + ')' : ''} | ${mark(same.text)} | ${mark(same.rs)} | ${mark(same.readouts)} | ${mark(same.markup)} | ${x.shapes}/${y.shapes} |`);
      lines.push(`${ok ? 'ok  ' : 'FAIL'}  ${PAGE_LABEL[page]} - ${x.name}  [r: ${y.rs.split(' ').slice(0, 4).join(' ') || '-'}]`);
      if (!ok) {
        const firstDiff = (p, q) => { let i = 0; while (i < p.length && p[i] === q[i]) i++; return `at ${i}: old "${p.slice(Math.max(0, i - 60), i + 80)}" | new "${q.slice(Math.max(0, i - 60), i + 80)}"`; };
        if (!same.readouts) lines.push('      readouts ' + firstDiff(x.readouts, y.readouts));
        else if (!same.text) lines.push('      svg text ' + firstDiff(x.text, y.text));
        else if (!same.markup) lines.push('      svg markup ' + firstDiff(x.markup, y.markup));
        if (x.actErr || y.actErr) lines.push('      control error: ' + (x.actErr || y.actErr));
      }
    }
    if (a.errors.length || b.errors.length) { failures++; lines.push(`FAIL  ${PAGE_LABEL[page]} console/page errors: old ${JSON.stringify(a.errors)} new ${JSON.stringify(b.errors)}`); }
  }
  const fc = await fileCheck(browser, newRoot, o.d3);
  md.push('', '| file:// page | drawn shapes | page errors |', '|---|--:|---|');
  for (const f of fc) { md.push(`| ${f.page} | ${f.shapes} | ${f.errors.length ? f.errors.join('; ') : 'none'} |`); if (!f.shapes || f.errors.length) { failures++; lines.push(`FAIL  file:// ${f.page}: ${f.shapes} shapes, errors ${JSON.stringify(f.errors)}`); } else lines.push(`ok    file:// ${f.page} draws ${f.shapes} shapes with no errors`); }
  await browser.close(); so.server.close(); sn.server.close();
  console.log(lines.join('\n'));
  console.log(`\n${states} states compared across ${Object.keys(STATES).length} pages; ${failures ? failures + ' FAILURE(S)' : 'all identical'}.`);
  if (o.report) fs.writeFileSync(o.report, md.join('\n') + '\n', { encoding: 'utf-8' });
  process.exit(failures ? 1 : 0);
}

if (require.main === module) main().catch(e => { console.error(e); process.exit(1); });
module.exports = { STATES, READOUTS, serve, capture, idle };
