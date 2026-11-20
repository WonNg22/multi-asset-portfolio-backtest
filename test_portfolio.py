"""Refresh a separate adjusted-price snapshot using Yahoo Finance."""
from pathlib import Path
import yfinance as yf

tickers = dict(SPY="US_EQ", EFA="INTL_EQ", AGG="BONDS", VNQ="REAL_EST", GLD="GOLD")
raw = yf.download(list(tickers), start="2005-01-01", end="2026-11-20",
                  interval="1d", auto_adjust=True, progress=False)
prices = raw["Close"].reindex(columns=tickers).rename(columns=tickers)
if prices.dropna().empty:
    raise ValueError("Download failed for one or more ETFs.")
path = Path("refreshed_prices.csv")
prices.to_csv(path, index_label="Date")
print(f"Saved {path}. Missing values by asset:")
print(prices.isna().sum())
