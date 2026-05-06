#!/usr/bin/env python3
"""
Craigside Portfolio — Daily Data Fetcher
=========================================
Fetches live prices, period returns, market cap, and analyst targets
for all portfolio tickers. Runs daily via GitHub Actions and writes
the result to data.json, which the dashboard reads on load.

Handles:
  - USD, EUR, GBP denominated stocks
  - GBP/USD and EUR/USD FX rates
  - Graceful fallback to last known price if a fetch fails
  - 7 return periods: 1W, 1M, 3M, 6M, 1Y, 3Y, 5Y
"""

import yfinance as yf
import json
import os
from datetime import datetime, timezone, timedelta
import time

# ── Ticker registry ──────────────────────────────────────────────────────────
# Maps portfolio ticker → yfinance symbol.
# If a stock trades on a non-US exchange you may need a suffix:
#   .L  = London Stock Exchange
#   .AX = ASX (Australia)
#   .ST = Stockholm / Nasdaq Nordic
# Leave as-is for US-listed stocks.
TICKER_MAP = {
    "APLD":  "APLD",   # Applied Digital
    "ORCL":  "ORCL",   # Oracle
    "IREN":  "IREN",   # IREN Ltd (Nasdaq)
    "NKE":   "NKE",    # Nike
    "MSFT":  "MSFT",   # Microsoft
    "ADBE":  "ADBE",   # Adobe
    "AAPL":  "AAPL",   # Apple
    "GOOGL": "GOOGL",  # Alphabet
    "AMZN":  "AMZN",   # Amazon
    "META":  "META",   # Meta
    "SHOP":  "SHOP",   # Shopify
    "SNAP":  "SNAP",   # Snap
    "NFLX":  "NFLX",   # Netflix
    "ALOY":  "ALOY",   # REalloys (may be unavailable — try ALOY.ST if needed)
    "FLY":   "FLY",    # Firefly Aerospace
    "ARKX":  "ARKX",   # ARK Space & Defence ETF
    "HOOD":  "HOOD",   # Robinhood
    "SOFI":  "SOFI",   # SoFi Technologies
    "TTWO":  "TTWO",   # Take-Two Interactive
    "SMR":   "SMR",    # NuScale Power
    "OKLO":  "OKLO",   # Oklo
    "LTBR":  "LTBR",   # Lightbridge
    "NVA":   "NVA",    # Nova Minerals (try NVA.AX if this fails)
    "UEC":   "UEC",    # Uranium Energy Corp
    "UUUU":  "UUUU",   # Energy Fuels
    "LEU":   "LEU",    # Centrus Energy
    "XE":    "XE",     # X-Energy
    "NVDA":  "NVDA",   # Nvidia
    "AVGO":  "AVGO",   # Broadcom
    "ASML":  "ASML",   # ASML Holding
}

# Return periods: (label, calendar_days_back)
PERIODS = [
    ("1W",  7),
    ("1M",  30),
    ("3M",  91),
    ("6M",  182),
    ("1Y",  365),
    ("3Y",  1095),
    ("5Y",  1825),
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def calc_return(hist, days_back):
    """% price return over last N calendar days. Returns None if not enough history."""
    if hist is None or len(hist) < 2:
        return None
    try:
        end_price = float(hist["Close"].iloc[-1])
        cutoff    = (hist.index[-1] - timedelta(days=days_back)).date()
        past      = hist[hist.index.date <= cutoff]
        if len(past) == 0:
            return None
        start_price = float(past["Close"].iloc[-1])
        if start_price <= 0:
            return None
        return round(((end_price - start_price) / start_price) * 100, 2)
    except Exception:
        return None


def fetch_rate(symbol, fallback):
    """Fetch an FX rate (e.g. GBPUSD=X) from yfinance with a fallback."""
    try:
        info = yf.Ticker(symbol).info or {}
        rate = info.get("regularMarketPrice") or info.get("previousClose")
        if rate:
            return round(float(rate), 4)
    except Exception:
        pass
    print(f"  ⚠ Could not fetch {symbol}, using fallback {fallback}")
    return fallback


def fetch_ticker(symbol):
    """
    Fetch price, currency, market cap, analyst target, and period returns
    for one ticker. Returns a dict; sets stale=True if price unavailable.
    """
    result = {
        "price":          None,
        "currency":       "USD",
        "mktCapB":        None,
        "analystTarget":  None,
        "returns":        {label: None for label, _ in PERIODS},
        "stale":          False,
    }

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}

        # Price (try multiple fields for robustness)
        price = (info.get("currentPrice")
                 or info.get("regularMarketPrice")
                 or info.get("navPrice")
                 or info.get("previousClose"))
        if price:
            result["price"] = round(float(price), 4)

        result["currency"]      = info.get("currency", "USD")
        result["analystTarget"] = round(float(info["targetMeanPrice"]), 2) if info.get("targetMeanPrice") else None
        mc = info.get("marketCap")
        if mc:
            result["mktCapB"] = round(mc / 1e9, 3)

        # Historical data for return calculations (up to 5 years)
        hist = ticker.history(period="5y", auto_adjust=True)
        if hasattr(hist.columns, "levels"):
            hist.columns = hist.columns.get_level_values(0)

        for label, days in PERIODS:
            result["returns"][label] = calc_return(hist, days)

        pct_1y = result["returns"].get("1Y")
        print(f"  ✓ {symbol:<6}  ${result['price']}  1Y={pct_1y}%")

    except Exception as e:
        result["stale"] = True
        print(f"  ✗ {symbol:<6}  Error: {e}")

    return result


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Craigside Portfolio — Data Fetcher")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    # Load existing data.json so we can fall back on cached prices
    existing_tickers = {}
    if os.path.exists("data.json"):
        try:
            with open("data.json") as f:
                existing_tickers = json.load(f).get("tickers", {})
        except Exception:
            pass

    # FX rates
    print("\nFX rates...")
    gbpusd = fetch_rate("GBPUSD=X", 1.26)
    eurusd = fetch_rate("EURUSD=X", 1.08)
    gbpeur = round(gbpusd / eurusd, 4)
    print(f"  GBP/USD={gbpusd}  EUR/USD={eurusd}  GBP/EUR={gbpeur}\n")

    # Ticker data
    print(f"Fetching {len(TICKER_MAP)} tickers...\n")
    tickers_out = {}

    for port_sym, yf_sym in TICKER_MAP.items():
        data = fetch_ticker(yf_sym)

        # If price failed, fall back to last known value
        if data["price"] is None and port_sym in existing_tickers:
            cached = existing_tickers[port_sym]
            data["price"]         = cached.get("price")
            data["currency"]      = cached.get("currency", "USD")
            data["mktCapB"]       = cached.get("mktCapB")
            data["analystTarget"] = cached.get("analystTarget")
            data["stale"]         = True
            print(f"    ↳ Cached price used: {data['price']}")

        tickers_out[port_sym] = data
        time.sleep(0.4)   # gentle rate limiting

    # Write output
    output = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gbpusd":      gbpusd,
        "eurusd":      eurusd,
        "gbpeur":      gbpeur,
        "tickers":     tickers_out,
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    live  = sum(1 for v in tickers_out.values() if not v.get("stale") and v.get("price"))
    stale = len(tickers_out) - live
    print(f"\n✓ data.json written — {live} live, {stale} cached/failed")


if __name__ == "__main__":
    main()
