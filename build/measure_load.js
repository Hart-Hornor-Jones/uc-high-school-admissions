// measure_load.js - cold-load measurement for the five published pages.
//
// For each page it opens a fresh browser context (no cache, no cookies), records every
// byte the browser receives until the first chart element is drawn, and the time from
// navigation start to that first drawn element. Optionally it emulates a slow connection
// (Lighthouse's mobile profile: 1.6 Mbit/s down, 750 kbit/s up, 150 ms round trip).
//
// usage:
//   node build/measure_load.js --dir <site root> [--throttle none|mobile|both] [--runs N]
//                              [--d3 <path to d3.min.js>] [--json <out.json>] [--label <text>]
//
// The pages load d3 from cdnjs; where that host is unreachable (offline CI, sandboxed
// containers) pass --d3 with a local copy of d3 7.8.5 and the harness serves it in place
// of the CDN response. Those bytes are then counted from the file size, but their transfer
// time is not simulated by the throttle, which is the same shortfall for every page measured.
//
// Requires: node 18+, the `playwright` package with its Chromium (npm i playwright &&
// npx playwright install chromium). No other dependencies.
'use strict';
const fs = require('fs');
const path = require('path');
const http = require('http');

const PAGES = [
  { name: 'root (index.html)', url: '',         chart: '#chart' },
  { name: 'context/',          url: 'context/', chart: '#chart' },
  { name: 'trends/',           url: 'trends/',  chart: '#chart' },
  { name: 'denied/',           url: 'denied/',  chart: '#cT'    },
  { name: 'history/',          url: 'history/', chart: '#cArc'  },
];
const MOBILE = { latency: 150, downloadThroughput: 1.6e6 / 8, uploadThroughput: 750e3 / 8, offline: false };
const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'application/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8', '.json': 'application/json; charset=utf-8', '.csv': 'text/csv; charset=utf-8',
  '.md': 'text/markdown; charset=utf-8', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };

function args() {
  const a = process.argv.slice(2), o = { throttle: 'both', runs: 1 };
  for (let i = 0; i < a.length; i++) {
    const k = a[i];
    if (k === '--dir') o.dir = a[++i];
    else if (k === '--throttle') o.throttle = a[++i];
    else if (k === '--runs') o.runs = parseInt(a[++i], 10);
    else if (k === '--d3') o.d3 = a[++i];
    else if (k === '--json') o.json = a[++i];
    else if (k === '--label') o.label = a[++i];
    else throw new Error('unknown argument ' + k);
  }
  if (!o.dir) throw new Error('--dir is required');
  return o;
}

// A dependency-free static server: no caching headers, no compression (GitHub Pages serves
// the repository files as they are, and the measurement must not assume otherwise).
function serve(root) {
  return new Promise(resolve => {
    const server = http.createServer((req, res) => {
      let p = decodeURIComponent(req.url.split('?')[0]);
      if (p.endsWith('/')) p += 'index.html';
      const file = path.join(root, p);
      if (!file.startsWith(root) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) {
        res.writeHead(404); res.end('not found'); return;
      }
      res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream',
        'Content-Length': fs.statSync(file).size, 'Cache-Control': 'no-store' });
      fs.createReadStream(file).pipe(res);
    });
    server.listen(0, '127.0.0.1', () => resolve({ server, base: 'http://127.0.0.1:' + server.address().port + '/' }));
  });
}

// Records, in the page, the moment the first graphical element appears inside the chart box.
const OBSERVER = ({ sel }) => {
  window.__firstChart = null;
  const hit = () => { const el = document.querySelector(sel); return !!(el && el.querySelector('circle,path,rect,line')); };
  const obs = new MutationObserver(() => { if (window.__firstChart == null && hit()) { window.__firstChart = performance.now(); obs.disconnect(); } });
  obs.observe(document, { childList: true, subtree: true });
};

async function measureOnce(browser, base, page, opts, throttle) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
  const pg = await ctx.newPage();
  const cdp = await ctx.newCDPSession(pg);
  await cdp.send('Network.enable');
  await cdp.send('Network.setCacheDisabled', { cacheDisabled: true });
  if (throttle) await cdp.send('Network.emulateNetworkConditions', MOBILE);
  const sizes = new Map(), urls = new Map();
  cdp.on('Network.responseReceived', e => urls.set(e.requestId, e.response.url));
  cdp.on('Network.loadingFinished', e => sizes.set(e.requestId, e.encodedDataLength));
  let d3bytes = 0;
  if (opts.d3) {
    await pg.route(/d3(\.min)?\.js$/, route => { d3bytes = fs.statSync(opts.d3).size; route.fulfill({ path: opts.d3, contentType: 'application/javascript' }); });
  }
  await pg.addInitScript(OBSERVER, { sel: page.chart });
  const bytesNow = () => { let b = 0; for (const [id, n] of sizes) { const u = urls.get(id) || ''; if (!/d3(\.min)?\.js$/.test(u)) b += n; } return b; };
  const t0 = Date.now();
  await pg.goto(base + page.url, { waitUntil: 'commit', timeout: 0 });
  await pg.waitForFunction(() => window.__firstChart != null, null, { timeout: 300000, polling: 50 });
  const firstChart = await pg.evaluate(() => window.__firstChart);
  const bytesAtChart = bytesNow();
  const wall = Date.now() - t0;
  await pg.waitForLoadState('load', { timeout: 300000 });
  await pg.waitForLoadState('networkidle', { timeout: 300000 });
  // pages that load their data in parts expose a promise that settles when nothing is pending
  await pg.evaluate(() => (window.UCPARTS && window.UCPARTS.whenIdle) ? window.UCPARTS.whenIdle() : null);
  await pg.waitForLoadState('networkidle', { timeout: 300000 });
  const bytesIdle = bytesNow();
  const requests = sizes.size;
  await ctx.close();
  return { firstChartMs: Math.round(firstChart), wallMs: wall, bytesAtChart, bytesIdle, d3bytes, requests };
}

function median(xs) { const s = xs.slice().sort((a, b) => a - b); const m = s.length >> 1; return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2; }
const kb = n => (n / 1024).toFixed(0) + ' KB';
const sec = ms => (ms / 1000).toFixed(2) + ' s';

async function main() {
  const opts = args();
  const { chromium } = require('playwright');
  const root = path.resolve(opts.dir);
  const { server, base } = await serve(root);
  const browser = await chromium.launch();
  const modes = opts.throttle === 'both' ? [false, true] : [opts.throttle === 'mobile'];
  const out = { label: opts.label || root, dir: root, results: [] };
  for (const throttle of modes) {
    for (const page of PAGES) {
      const runs = [];
      for (let i = 0; i < opts.runs; i++) runs.push(await measureOnce(browser, base, page, opts, throttle));
      const r = { page: page.name, throttle: throttle ? 'mobile 1.6 Mbit/s, 150 ms RTT' : 'none (localhost)',
        firstChartMs: median(runs.map(x => x.firstChartMs)), bytesAtChart: median(runs.map(x => x.bytesAtChart)),
        bytesIdle: median(runs.map(x => x.bytesIdle)), d3bytes: runs[0].d3bytes, requests: median(runs.map(x => x.requests)), runs };
      out.results.push(r);
      process.stderr.write(`${r.throttle} | ${r.page} | first chart ${sec(r.firstChartMs)} | ${kb(r.bytesAtChart)} to chart, ${kb(r.bytesIdle)} at idle\n`);
    }
  }
  await browser.close();
  server.close();
  console.log(`\n### ${out.label}\n`);
  console.log('| Connection | Page | Bytes to first chart | Bytes at idle | Time to first chart | Requests |');
  console.log('|---|---|--:|--:|--:|--:|');
  for (const r of out.results) console.log(`| ${r.throttle} | ${r.page} | ${kb(r.bytesAtChart)} | ${kb(r.bytesIdle)} | ${sec(r.firstChartMs)} | ${r.requests} |`);
  if (out.results.some(r => r.d3bytes)) console.log(`\nd3 7.8.5 (${kb(out.results[0].d3bytes)}) was served from a local copy and is not included in the byte columns.`);
  if (opts.json) fs.writeFileSync(opts.json, JSON.stringify(out, null, 1), { encoding: 'utf-8' });
}

main().catch(e => { console.error(e); process.exit(1); });
