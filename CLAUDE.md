# CLAUDE.md — Craigside Portfolio Dashboard

## What this project is

A single-page portfolio dashboard hosted on GitHub Pages at:
`https://dannypeters15.github.io/danny-trading212portfolio-dashboard/`

Data is updated daily by a GitHub Actions workflow that runs `fetch_data.py` (using yfinance) and commits `data.json` back to the repo. The HTML page reads `data.json` on load — no backend, no build step.

---

## File map

| File | Role |
|---|---|
| `index.html` | The entire dashboard — all HTML, CSS, and JS in one file |
| `fetch_data.py` | Python script run by GitHub Actions; writes `data.json` |
| `data.json` | Auto-generated daily; **do not manually edit** |
| `portfolio.json` | Snapshot of portfolio config; user downloads from Editor tab and commits here for backup |
| `watchlist.json` | Simple list of ticker symbols for the watchlist section |
| `.github/workflows/update_data.yml` | Runs daily at 9:30pm UTC (weekdays), can be triggered manually |
| `requirements.txt` | `yfinance>=0.2.37`, `requests>=2.31.0` |

---

## Architecture of index.html

Everything lives in one file — no bundler, no framework. Key sections top to bottom:

1. **CSS** — inline `<style>` block, minified
2. **HTML shell** — header, stats band, tab bar, `#content` div, loading overlay
3. **JS** — all logic in `<script>` at the bottom

### JS structure

- **Constants / colors**: `POS`, `NEG`, `ACCENT`, `TEXT`, `MUTED`, `BORDER`
- **`INIT_PORTFOLIO`**: hardcoded default data (30 tickers). Loaded into `portfolio` array on first visit; thereafter localStorage is the source of truth
- **`computed()`**: central transform — maps `portfolio` against `liveData` to produce enriched objects (`en` array). All tabs read from this
- **`updateStats()`**: updates the 4 stat cards (total value, positions, P&L, ATH value, weighted avg upside)
- **`renderXxx()` functions**: one per tab — return HTML strings
- **`drawCharts()`**: Chart.js calls, runs after `setTab()` via `setTimeout(..., 40)`
- **`init()`**: async startup — loads localStorage, fetches `data.json`, renders first tab

### Tabs (in order)
`Overview` | `Upside` | `ATH Analysis` | `Returns` | `P&L` | `Editor`

### LocalStorage keys
- `t212-portfolio-v1` — portfolio holdings array
- `t212-categories-v1` — sector categories
- `t212-watchlist-v1` — watchlist items (separate from `watchlist.json`)

---

## Deployment

Pushing to `main` automatically updates GitHub Pages (~1 min propagation). There is no CI check to wait for — just `git push`.

Data updates happen separately via GitHub Actions. To trigger manually: Actions → Update Portfolio Data → Run workflow.

---

## Important coding constraints

### String quoting in JS template literals
`index.html` uses single-quoted JS strings that build HTML strings internally. This causes two sharp edges:

1. **Single quotes in HTML `onclick` attributes**: use `&#39;` not `'`
   - Wrong: `onclick="fn('${x}')"` inside a `'...'` JS string
   - Right: `onclick="fn(&#39;${x}&#39;)"`

2. **Single quotes in CSS values inside JS strings**: use `\'`
   - Wrong: `style="font-family:'Courier New'"` inside a `'...'` JS string
   - Right: `style="font-family:\'Courier New\'"`

3. **Adjacent string literals without `+`**: will cause `SyntaxError: Unexpected string`
   - Wrong: `'some text''more text'`
   - Right: `'some text'+'more text'`

### No target/planned features in the portfolio section
`plannedTotal` and `targetPct` fields **exist in `INIT_PORTFOLIO`** (for legacy data compatibility) but are intentionally not exposed in the portfolio Editor tab UI. Target allocation is handled entirely in the Watchlist section. Do not re-add Planned £, Target %, Gap Analysis, Planned vs Current, or DCA Planner tabs to the portfolio section.

### Chart.js version
Using Chart.js **4.4.1** via CDN. API differs from v2/v3 in places (e.g., `scales.x` not `scales.xAxes`).

---

## data.json shape

```json
{
  "lastUpdated": "2025-05-10T21:32:00Z",
  "gbpusd": 1.2734,
  "eurusd": 1.0821,
  "gbpeur": 1.1768,
  "tickers": {
    "AAPL": {
      "price": 189.50,
      "currency": "USD",
      "mktCapB": 2940,
      "analystTarget": 210.0,
      "athPrice": 237.23,
      "returns": { "1W": 1.2, "1M": -3.1, "3M": 5.4, ... },
      "stale": false
    }
  },
  "watchlist": { ... same shape per ticker ... }
}
```

If a ticker shows `stale: true`, yfinance couldn't fetch it and the last known price is used.

---

## Adding a new portfolio ticker

1. Add it to `INIT_PORTFOLIO` in `index.html` (or add via the Editor tab in the browser)
2. Add it to `TICKER_MAP` in `fetch_data.py` so daily data is fetched for it
3. Commit and push both files

### Known tricky tickers

| Ticker | Issue |
|---|---|
| `ALOY` | May need `ALOY.ST` in fetch_data.py (Nasdaq Nordic) |
| `NVA` | May need `NVA.AX` if ASX-listed |
| `FLY` | Check current exchange listing — may need suffix |
| `ARKX`, `ALOY`, `FLY`, `NVA` | Use `manualHolding` override; T212 value differs from shares × price |
