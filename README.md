# Craigside Portfolio Dashboard

A live portfolio dashboard hosted on GitHub Pages, with daily automatic price updates and period return calculations via GitHub Actions.

---

## How it works

| Component | What it does |
|---|---|
| `index.html` | The dashboard — runs entirely in your browser |
| `fetch_data.py` | Python script that fetches live prices & returns from Yahoo Finance |
| `data.json` | Auto-generated daily — the dashboard reads this on load |
| `portfolio.json` | Your portfolio config (shares, targets, cost basis) — edit via the dashboard |
| `.github/workflows/update_data.yml` | Runs `fetch_data.py` every weekday evening, commits `data.json` |

**Data flow:**
```
GitHub Actions (daily, 9:30pm UTC)
  → fetch_data.py runs
  → Pulls prices + returns from Yahoo Finance for all 30 tickers
  → Calculates 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y returns
  → Fetches GBP/USD and EUR/USD rates
  → Writes data.json → commits to repo
  → index.html reads data.json on next page load
```

---

## One-time setup (takes ~5 minutes)

### Step 1 — Create the repository

Create a new repo on GitHub named `craigside-portfolio` (or whatever you like). Make it **public** (required for free GitHub Pages).

Upload all these files keeping the folder structure:
```
craigside-portfolio/
├── index.html
├── fetch_data.py
├── requirements.txt
├── portfolio.json
├── data.json          ← upload the empty one, it gets replaced automatically
├── README.md
└── .github/
    └── workflows/
        └── update_data.yml
```

> **Tip:** The easiest way is to drag all files into the GitHub web interface, or use `git push` if you're comfortable with that.

### Step 2 — Enable GitHub Pages

1. Go to your repo → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` | Folder: `/ (root)`
4. Click **Save**
5. Wait ~1 minute — your site will be live at `https://dannypeters15.github.io/craigside-portfolio/`

### Step 3 — Enable Actions write permission

1. Go to **Settings** → **Actions** → **General**
2. Scroll to **Workflow permissions**
3. Select **Read and write permissions**
4. Click **Save**

### Step 4 — Run the workflow for the first time

1. Go to the **Actions** tab in your repo
2. Click **Update Portfolio Data** in the left sidebar
3. Click **Run workflow** → **Run workflow** (green button)
4. Wait ~2 minutes for it to complete
5. Refresh your GitHub Pages site — live data will now show

After this, it runs automatically every weekday at 9:30pm UTC (10:30pm BST).

---

## Updating your portfolio

### Prices, returns, market cap, analyst targets
These update **automatically every day**. You don't need to do anything.

### Shares, cost basis, targets, new positions
1. Open your dashboard
2. Go to the **Editor tab**
3. Edit any field — click away to save (stored in your browser)
4. When you're happy, click **↓ portfolio.json** to download your updated config
5. Commit the downloaded `portfolio.json` to your repo to keep it backed up

### Adding a new ticker
1. Add it in the Editor tab
2. Also add it to the `TICKER_MAP` in `fetch_data.py` so prices are fetched for it

---

## Ticker notes

Some tickers may not be available on Yahoo Finance. If `data.json` shows `stale: true` for a ticker, the last known price is being used. To fix:

| Ticker | Possible fix |
|---|---|
| `ALOY` | Try changing to `ALOY.ST` in `fetch_data.py` (Nasdaq Nordic) |
| `NVA` | Try `NVA.AX` if it's ASX-listed Nova Minerals |
| `FLY` | Check current exchange listing — may need suffix |
| `XE` | X-Energy — recently listed, should work |

---

## Manual trigger

You can run the data update any time:
1. Go to **Actions** → **Update Portfolio Data** → **Run workflow**

---

## Files you should NOT manually edit

- `data.json` — auto-generated, gets overwritten on every run
