# Cold-load measurements

How long each page takes to draw its first chart on a cold cache, and how many bytes it needs to
get there, before and after the data layer was split into parts (revision of 2026-11-05).

## Method

`build/measure_load.js` serves a checkout of the site from a local static server with no caching
and no compression (GitHub Pages serves the repository files as they are; no precomputed gzip is
assumed), opens each page in a fresh browser context, and records the bytes received until the
first graphical element appears inside the chart box and the time from navigation start to that
moment (a `MutationObserver` installed before the page runs). "At idle" counts everything the page
fetched on its own before settling. The throttled rows emulate Lighthouse's mobile profile through
the DevTools protocol: 1.6 Mbit/s down, 750 kbit/s up, 150 ms round trip. Each figure is the median
of three runs (one run for the throttled "before" rows, which take up to a minute each).

d3 7.8.5 (273 KB) was served from a local copy in place of the cdnjs response, because that host
was unreachable from the measuring machine; its bytes are left out of every row and its transfer
time is not simulated by the throttle. The shortfall is the same for every page and both revisions.

The "before" checkout is commit `04f2bdb` (the last revision with one script per page).

## Before (one data script per page)

| Connection | Page | Bytes to first chart | Bytes at idle | Time to first chart | Requests |
|---|---|--:|--:|--:|--:|
| none (localhost) | root (index.html) | 8986 KB | 8986 KB | 0.67 s | 3 |
| none (localhost) | context/ | 11072 KB | 11072 KB | 0.59 s | 4 |
| none (localhost) | trends/ | 2333 KB | 2333 KB | 0.14 s | 3 |
| none (localhost) | denied/ | 4754 KB | 4754 KB | 0.33 s | 2 |
| none (localhost) | history/ | 154 KB | 154 KB | 0.09 s | 2 |
| mobile 1.6 Mbit/s, 150 ms RTT | root (index.html) | 8986 KB | 8986 KB | 46.51 s | 3 |
| mobile 1.6 Mbit/s, 150 ms RTT | context/ | 11072 KB | 11072 KB | 57.19 s | 4 |
| mobile 1.6 Mbit/s, 150 ms RTT | trends/ | 2333 KB | 2333 KB | 12.20 s | 3 |
| mobile 1.6 Mbit/s, 150 ms RTT | denied/ | 4754 KB | 4754 KB | 24.75 s | 2 |
| mobile 1.6 Mbit/s, 150 ms RTT | history/ | 154 KB | 154 KB | 1.00 s | 2 |

## After (core script plus parts on demand)

| Connection | Page | Bytes to first chart | Bytes at idle | Time to first chart | Requests |
|---|---|--:|--:|--:|--:|
| none (localhost) | root (index.html) | 1089 KB | 1089 KB | 0.21 s | 6 |
| none (localhost) | context/ | 1624 KB | 1624 KB | 0.22 s | 12 |
| none (localhost) | trends/ | 409 KB | 409 KB | 0.09 s | 4 |
| none (localhost) | denied/ | 585 KB | 585 KB | 0.17 s | 4 |
| none (localhost) | history/ | 154 KB | 154 KB | 0.09 s | 2 |
| mobile 1.6 Mbit/s, 150 ms RTT | root (index.html) | 1089 KB | 1089 KB | 6.04 s | 6 |
| mobile 1.6 Mbit/s, 150 ms RTT | context/ | 1624 KB | 1624 KB | 8.81 s | 12 |
| mobile 1.6 Mbit/s, 150 ms RTT | trends/ | 409 KB | 409 KB | 2.29 s | 4 |
| mobile 1.6 Mbit/s, 150 ms RTT | denied/ | 585 KB | 585 KB | 3.42 s | 4 |
| mobile 1.6 Mbit/s, 150 ms RTT | history/ | 154 KB | 154 KB | 1.00 s | 2 |

## What the root page still costs

At 1.6 Mbit/s the root page's 6.0 s is almost all transfer: `index.html` (114 KB),
`data.js` (181 KB: school names, coordinates, metrics, periods), `data_parts/schools.js`
(489 KB: every school-year's covariates, which the per-year correlation panel reads for all eleven
years) and `data_parts/campus_0.js` (297 KB: Berkeley's funnel). The remaining 489 KB could only be
cut further by shipping the covariates per year as well, at the cost of eleven more requests on the
root page; the context page already does this for its tract rows because a period reads only its
own years there.

The history page was already small (154 KB) and is unchanged.

## Reproducing

```bash
git worktree add ../old 04f2bdb
node build/measure_load.js --dir ../old --throttle both --runs 3 --label before
node build/measure_load.js --dir .      --throttle both --runs 3 --label after
```

Add `--d3 <path to d3.min.js>` where cdnjs is unreachable. The verification that the pages still
draw the same thing is `node build/compare_pages.js --old ../old --new .`, and
`python3 build/check_data_parts.py --old ../old` compares every value of the data layer.
