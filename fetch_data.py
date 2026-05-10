#!/usr/bin/env python3
"""
Danny's Portfolio -- Daily Data Fetcher
=========================================
Fetches live prices, period returns, market cap, analyst targets,
all-time high prices for all portfolio and watchlist tickers.
Runs daily via GitHub Actions and writes the result to data.json.
"""

import yfinance as yf
import json
import os
from datetime import datetime, timezone, timedelta
import time

# -- Ticker registry ----------------------------------------------------------
TICKER_MAP = {
    "APLD":  "APLD",
    "ORCL":  "ORCL",
    "IREN":  "IREN",
    "MSFT":  "MSFT",
    "ADBE":  "ADBE",
    "GOOGL": "GOOGL",
    "AMZN":  "AMZN",
    "SNAP":  "SNAP",
    "NFLX":  "NFLX",
    "ALOY":  "ALOY",
    "FLY":   "FLY",
    "TTWO":  "TTWO",
    "SMR":   "SMR",
    "OKLO":  "OKLO",
    "LTBR":  "LTBR",
    "NVA":   "NVA",
    "UEC":   "UEC",
    "LEU":   "LEU",
    "XE":    "XE",
    "NVDA":  "NVDA",
    "AVGO":  "AVGO",
    "AVAV":  "AVAV",
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


# -- Helpers ------------------------------------------------------------------

def calc_return(hist, days_back):
    if hist is None or len(hist) < 2:
        return None
    try:
        end_price   = float(hist["Close"].iloc[-1])
        cutoff      = (hist.index[-1] - timedelta(days=days_back)).date()
        past        = hist[hist.index.date <= cutoff]
        if len(past) == 0:
            return None
        start_price = float(past["Close"].iloc[-1])
        if start_price <= 0:
            return None
        return round(((end_price - start_price) / start_price) * 100, 2)
    except Exception:
        return None


def fetch_rate(symbol, fallback):
    try:
        info = yf.Ticker(symbol).info or {}
        rate = info.get("regularMarketPrice") or info.get("previousClose")
        if rate:
            return round(float(rate), 4)
    except Exception:
        pass
    print(f"  Could not fetch {symbol}, using fallback {fallback}")
    return fallback


def fetch_ticker(symbol):
    result = {
        "price":         None,
        "currency":      "USD",
        "mktCapB":       None,
        "analystTarget": None,
        "athPrice":      None,
        "sector":        "",
        "returns":       {"1D": None, **{label: None for label, _ in PERIODS}},
        "stale":         False,
    }

    try:
        ticker = yf.Ticker(symbol)
        info   = ticker.info or {}

        price = (info.get("currentPrice")
                 or info.get("regularMarketPrice")
                 or info.get("navPrice")
                 or info.get("previousClose"))
        if price:
            result["price"] = round(float(price), 4)

        result["currency"]      = info.get("currency", "USD")
        result["analystTarget"] = round(float(info["targetMeanPrice"]), 2) if info.get("targetMeanPrice") else None
        result["sector"]        = info.get("sector", "")
        mc = info.get("marketCap")
        if mc:
            result["mktCapB"] = round(mc / 1e9, 3)

        # 5-year history for period returns
        hist5y = ticker.history(period="5y", auto_adjust=True)
        if hasattr(hist5y.columns, "levels"):
            hist5y.columns = hist5y.columns.get_level_values(0)

        # 1D return from last 2 trading day closes
        if hist5y is not None and len(hist5y) >= 2:
            c0 = float(hist5y["Close"].iloc[-2])
            c1 = float(hist5y["Close"].iloc[-1])
            if c0 > 0:
                result["returns"]["1D"] = round((c1 - c0) / c0 * 100, 2)

        for label, days in PERIODS:
            result["returns"][label] = calc_return(hist5y, days)

        # All-time high
        try:
            hist_max = ticker.history(period="max", auto_adjust=True)
            if hasattr(hist_max.columns, "levels"):
                hist_max.columns = hist_max.columns.get_level_values(0)
            if hist_max is not None and len(hist_max) > 0:
                result["athPrice"] = round(float(hist_max["Close"].max()), 4)
        except Exception as e:
            print(f"    ATH fetch failed for {symbol}: {e}")

        r1d = result["returns"].get("1D")
        r1y = result["returns"].get("1Y")
        print(f"  {symbol:<6}  price={result['price']}  1D={r1d}%  1Y={r1y}%  ATH={result['athPrice']}  sector={result['sector']}")

    except Exception as e:
        print(f"  ERROR fetching {symbol}: {e}")
        result["stale"] = True

    return result


# -- Main ---------------------------------------------------------------------

def main():
    print("=" * 55)
    print("  Danny Portfolio -- Data Fetcher")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 55)

    existing_tickers   = {}
    existing_watchlist = {}
    if os.path.exists("data.json"):
        try:
            with open("data.json") as f:
                d = json.load(f)
                existing_tickers   = d.get("tickers", {})
                existing_watchlist = d.get("watchlist", {})
        except Exception:
            pass

    print("\nFX rates...")
    gbpusd = fetch_rate("GBPUSD=X", 1.26)
    eurusd = fetch_rate("EURUSD=X", 1.08)
    gbpeur = round(gbpusd / eurusd, 4)
    print(f"  GBP/USD={gbpusd}  EUR/USD={eurusd}  GBP/EUR={gbpeur}\n")

    print(f"Fetching {len(TICKER_MAP)} portfolio tickers...\n")
    tickers_out = {}

    for port_sym, yf_sym in TICKER_MAP.items():
        data = fetch_ticker(yf_sym)
        if data["price"] is None and port_sym in existing_tickers:
            cached = existing_tickers[port_sym]
            data["price"]         = cached.get("price")
            data["currency"]      = cached.get("currency", "USD")
            data["mktCapB"]       = cached.get("mktCapB")
            data["analystTarget"] = cached.get("analystTarget")
            data["athPrice"]      = cached.get("athPrice")
            data["sector"]        = cached.get("sector", "")
            data["stale"]         = True
            print(f"    Cached price used: {data['price']}")
        tickers_out[port_sym] = data
        time.sleep(0.5)

    # Watchlist tickers
    watchlist_tickers = []
    if os.path.exists("watchlist.json"):
        try:
            with open("watchlist.json") as f:
                watchlist_tickers = json.load(f)
            print(f"\nFetching {len(watchlist_tickers)} watchlist tickers...\n")
        except Exception as e:
            print(f"  Could not read watchlist.json: {e}")

    watchlist_out = {}
    for wl_sym in watchlist_tickers:
        data = fetch_ticker(wl_sym)
        if data["price"] is None and wl_sym in existing_watchlist:
            cached = existing_watchlist[wl_sym]
            data["price"]         = cached.get("price")
            data["currency"]      = cached.get("currency", "USD")
            data["sector"]        = cached.get("sector", "")
            data["analystTarget"] = cached.get("analystTarget")
            data["stale"]         = True
            print(f"    Cached price used: {data['price']}")
        watchlist_out[wl_sym] = data
        time.sleep(0.5)

    output = {
        "lastUpdated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "gbpusd":      gbpusd,
        "eurusd":      eurusd,
        "gbpeur":      gbpeur,
        "tickers":     tickers_out,
        "watchlist":   watchlist_out,
    }

    with open("data.json", "w") as f:
        json.dump(output, f, indent=2)

    print(f"\nWrote data.json  ({len(tickers_out)} portfolio + {len(watchlist_out)} watchlist tickers)")


if __name__ == "__main__":
    main()
