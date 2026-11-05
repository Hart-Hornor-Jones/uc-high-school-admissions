// test_unused_fields.js - the fields left out of the split data layer are fields no page reads.
//
// Two fields were dropped when the data layer was split:
//   * context/data_context.js: the tract population column `pop` of every ctx row
//   * trends/data_trends.js:   meta.counts, a bookkeeping dict of table sizes
// This proves it two ways. Statically, the page sources are searched for any reference to the
// field. Dynamically, the pre-split pages are opened headless with the field instrumented
// (a Proxy on every ctx row, a getter on meta.counts) and driven through the same control
// sequence build/compare_pages.js uses; a read of the field anywhere - chart, statistics,
// profile card, export - would be counted. The test passes only when both find nothing.
//
// usage:
//   node build/test_unused_fields.js --old <checkout of the pre-split site> [--d3 <d3.min.js>]
//
// Requires: node 18+, playwright with its Chromium.
'use strict';
const fs = require('fs');
const path = require('path');
const { STATES, serve, idle } = require('./compare_pages.js');

function args() {
  const a = process.argv.slice(2), o = {};
  for (let i = 0; i < a.length; i++) {
    if (a[i] === '--old') o.old = a[++i];
    else if (a[i] === '--d3') o.d3 = a[++i];
    else throw new Error('unknown argument ' + a[i]);
  }
  if (!o.old) throw new Error('--old is required');
  return o;
}

// static: references to the field in the page source (array `.pop()` calls are not the field)
function staticRefs(src, field) {
  const re = new RegExp(`(['"\`.])${field}\\b(?!\\s*\\()`, 'g');
  const hits = [];
  let m;
  while ((m = re.exec(src))) hits.push(src.slice(Math.max(0, m.index - 40), m.index + 40).replace(/\s+/g, ' '));
  return hits;
}

// instrumentation appended to the old data scripts as they are served
const INSTRUMENT = {
  'context/data_context.js': `
;(function(){ const X = window.UCCTX, pi = String(X.cvars.indexOf('pop')); window.__popReads = 0;
  for (const k in X.ctx) X.ctx[k] = X.ctx[k].map(r => new Proxy(r, { get(t, p, rcv) { if (p === pi) window.__popReads++; return Reflect.get(t, p, rcv); } }));
})();`,
  'trends/data_trends.js': `
;(function(){ const T = window.TRENDS_DATA, v = T.meta.counts; window.__countsReads = 0;
  Object.defineProperty(T.meta, 'counts', { get() { window.__countsReads++; return v; }, enumerable: true });
})();`,
};

async function main() {
  const o = args();
  const root = path.resolve(o.old);
  let failed = false;
  // ---- static
  const checks = [
    ['context/index.html', 'pop', 'tract population column of ctx rows'],
    ['index.html', 'pop', 'tract population column (the explorer does not load data_context.js at all)'],
    ['trends/index.html', 'counts', 'meta.counts'],
  ];
  for (const [file, field, what] of checks) {
    const hits = staticRefs(fs.readFileSync(path.join(root, file), { encoding: 'utf-8' }), field);
    if (hits.length) { failed = true; console.log(`FAIL  ${file} references "${field}" (${what}): ${JSON.stringify(hits.slice(0, 3))}`); }
    else console.log(`ok    ${file}: no reference to "${field}" (${what})`);
  }
  // ---- dynamic
  const { chromium } = require('playwright');
  const { server, base } = await serve(root);
  const browser = await chromium.launch();
  for (const [page, counter] of [['context/', '__popReads'], ['trends/', '__countsReads']]) {
    const pg = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    pg.on('pageerror', e => errors.push(String(e.message)));
    if (o.d3) await pg.route(/d3(\.min)?\.js$/, r => r.fulfill({ path: o.d3, contentType: 'application/javascript' }));
    for (const file of Object.keys(INSTRUMENT)) {
      await pg.route(url => url.pathname.endsWith('/' + file), r => {
        const body = fs.readFileSync(path.join(root, file), { encoding: 'utf-8' }) + INSTRUMENT[file];
        r.fulfill({ body, contentType: 'application/javascript; charset=utf-8' });
      });
    }
    await pg.goto(base + page, { waitUntil: 'load' });
    let states = 0;
    for (const [, act] of STATES[page]) { await act(pg); await idle(pg); await pg.waitForTimeout(60); states++; }
    // the exports read the drawn data too
    if (page === 'context/') await pg.evaluate(() => { const b = document.querySelector('#exportMenu button, .export button'); if (b) b.click(); });
    const reads = await pg.evaluate(c => window[c], counter);
    const total = await pg.evaluate(() => Object.keys(window.UCCTX ? window.UCCTX.ctx : {}).length);
    if (reads !== 0 || errors.length) { failed = true; console.log(`FAIL  ${page}: ${reads} read(s) of the dropped field over ${states} states; errors ${JSON.stringify(errors)}`); }
    else console.log(`ok    ${page}: 0 reads of the dropped field over ${states} states${total ? ` (${total} instrumented schools)` : ''}`);
    await pg.close();
  }
  await browser.close(); server.close();
  console.log(failed ? '\nFAILED' : '\nevery dropped field is unread');
  process.exit(failed ? 1 : 0);
}

main().catch(e => { console.error(e); process.exit(1); });
