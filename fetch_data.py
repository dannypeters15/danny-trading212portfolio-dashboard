#!/usr/bin/env python3
"""
Craigside Portfolio — Daily Data Fetcher
=========================================
Fetches live prices, period returns, market cap, analyst targets,
and all-time high prices for all portfolio tickers.
Runs daily via GitHub Actions and writes the result to data.json.
"""

import yfinance as yf
import json
import os
from datetime import datetime, timezone, timedelta
import time

# ── Ticker registry ──────────────────────────────────────────────────────────
# Maps portfolio ticker → yfinance symbol.
# NOTE: Some tickers on Trading 212 UK use different share classes or
# GBX (pence) pricing vs the US-listed equivalent. If a ticker's
# auto-calculated holding doesn't match T212, use the manual override
# field in the dashboard Editor tab.
TICKER_MAP = {
    "APLD":  "APLD",
    "ORCL":  "ORCL",
    "IREN":  "IREN",
    "NKE":   "NKE",
    "MSFT":  "MSFT",
    "ADBE":  "ADBE",
    "AAPL":  "AAPL",
    "GOOGL": "GOOGL",
    "AMZN":  "AMZN",
    "META":  "META",
    "SHOP":  "SHOP",
    "SNAP":  "SNAP",
    "NFLX":  "NFLX",
    "ALOY":  "ALOY",   # REalloys — try ALOY.ST if unavailable
    "FLY":   "FLY",    # Firefly Aerospace
    "ARKX":  "ARKX",   # ARK Space ETF — T212 UK may use different denomination
    "HOOD":  "HOOD",
    "SOFI":  "SOFI",
    "TTWO":  "TTWO",
    "SMR":   "SMR",
    "OKLO":  "OKLO",
    "LTBR":  "LTBR",
    "NVA":   "NVA",    # Try NVA.AX if unavailable
    "UEC":   "UEC",
    "UUUU":  "UUUU",
    "LEU":   "LEU",
    "XE":    "XE",
    "NVDA":  "NVDA",
    "AVGO":  "AVGO",
    "ASML":  "ASML",
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


# ── Helpers ───────────────────────────────────────────────────────────────────

def calc_return(hist, days_back):
    """% price return over last N calendar days."""
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
    """Fetch an FX rate from yfinance."""
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
    Fetch all data for one ticker including:
    - Current price, currency, market cap, analyst target
    - Period returns (1W through 5Y)
    - All-time high price (athPrice) — dashboard calculates ATH holding as shares × athPrice
    """
    result = {
        "price":         None,
        "currency":      "USD",
        "mktCapB":       None,
        "analystTarget": None,
        "athPrice":      None,   # All-time high closing price
        "returns":       {label: None for label, _ in PERIODS},
        "stale":         False,
    }

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}

        # Current price
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

        # 5-year history for period return calculations
        hist5y = ticker.history(period="5y", auto_adjust=True)
        if hasattr(hist5y.columns, "levels"):
            hist5y.columns = hist5y.columns.get_level_values(0)

        for label, days in PERIODS:
            result["returns"][label] = calc_return(hist5y, days)

        # All-time high — fetch full history, find max closing price
        try:
            hist_max = ticker.history(period="max", auto_adjust=True)
            if hasattr(hist_max.columns, "levels"):
                hist_max.columns = hist_max.columns.get_level_values(0)
            if hist_max is not None and len(hist_max) > 0:
                result["athPrice"] = round(float(hist_max["Close"].max()), 4)
        except Exception as e:
            print(f"    ⚠ ATH fetch failed for {symbol}: {e}")

        pct_1y = result["returns"].get("1Y")
        ath    = result["athPrice"]
        print(f"  ✓ {symbol:<6}  ${result['price']}  1Y={pct_1y}%  ATH=${ath}")

    except Exception as e:
        result["stale"] = True
        print(f"  ✗ {symbol:<6}  Error: {e}")

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  Craigside Portfolio — Data Fetcher")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    # Load existing data.json for fallback prices
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

        # Fall back to cached values if fetch failed
        if data["price"] is None and port_sym in existing_tickers:
            cached = existing_tickers[port_sym]
            data["price"]         = cached.get("price")
            data["currency"]      = cached.get("currency", "USD")
            data["mktCapB"]       = cached.get("mktCapB")
            data["analystTarget"] = cached.get("analystTarget")
            data["athPrice"]      = cached.get("athPrice")
            data["stale"]         = True
            print(f"    ↳ Cached price used: {data['price']}")

        tickers_out[port_sym] = data
        time.sleep(0.5)  # gentle rate limiting

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
