"""
data_loader.py
Fetch OHLCV price data for backtesting, with local CSV caching.

Supports:
- US / S&P500 tickers via yfinance
- Vietnam tickers via vnstock (SSI/TCBS source) -- optional, only imported if used

Usage:
    from data_loader import load_price_data
    df = load_price_data("AAPL", start="2015-01-01", end="2024-12-31", market="us")
    df = load_price_data("FPT",  start="2018-01-01", end="2024-12-31", market="vn")
"""

from __future__ import annotations
import os
import pandas as pd

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_path(ticker: str, market: str) -> str:
    return os.path.join(CACHE_DIR, f"{market}_{ticker}.csv")


def _standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure canonical columns: open, high, low, close, volume; DatetimeIndex named 'date'."""
    df = df.copy()
    df.columns = [str(c).lower() for c in df.columns]
    rename_map = {}
    for col in df.columns:
        if "adj" in col and "close" in col:
            continue  # keep separate, we use raw close for signals
        if col in ("open", "high", "low", "close", "volume"):
            rename_map[col] = col
    df = df.rename(columns=rename_map)
    required = ["open", "high", "low", "close", "volume"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing expected columns after standardization: {missing}")
    df = df[required]
    df.index.name = "date"
    df = df.sort_index()
    df = df[~df.index.duplicated(keep="last")]
    return df


def _fetch_us(ticker: str, start: str, end: str) -> pd.DataFrame:
    import yfinance as yf
    raw = yf.download(ticker, start=start, end=end, auto_adjust=True, progress=False)
    if raw.empty:
        raise RuntimeError(f"No data returned for {ticker} from yfinance.")
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = [c[0] for c in raw.columns]
    return _standardize_columns(raw)


def _fetch_vn(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Fetch VN stock via vnstock (community library wrapping SSI/TCBS/VCI endpoints).
    Install: pip install vnstock
    """
    from vnstock import Vnstock
    stock = Vnstock().stock(symbol=ticker, source="VCI")
    raw = stock.quote.history(start=start, end=end, interval="1D")
    raw = raw.rename(columns={"time": "date"}).set_index("date")
    raw.index = pd.to_datetime(raw.index)
    return _standardize_columns(raw)


def load_price_data(
    ticker: str,
    start: str,
    end: str,
    market: str = "us",
    force_refresh: bool = False,
) -> pd.DataFrame:
    """
    Load OHLCV data for a single ticker, using local cache when available.

    Parameters
    ----------
    ticker : str            e.g. "AAPL", "SPY", "FPT", "VNM"
    start, end : str        "YYYY-MM-DD"
    market : str             "us" or "vn"
    force_refresh : bool     ignore cache and re-download

    Returns
    -------
    pd.DataFrame indexed by date with columns [open, high, low, close, volume]
    """
    path = _cache_path(ticker, market)

    if not force_refresh and os.path.exists(path):
        df = pd.read_csv(path, index_col="date", parse_dates=True)
        # Cache may cover a wider range than requested; slice it.
        df = df.loc[start:end]
        if not df.empty:
            return df

    if market == "us":
        df = _fetch_us(ticker, start, end)
    elif market == "vn":
        df = _fetch_vn(ticker, start, end)
    else:
        raise ValueError("market must be 'us' or 'vn'")

    df.to_csv(path)
    return df.loc[start:end]


def load_multiple(tickers, start, end, market="us"):
    """Load several tickers into a dict of DataFrames."""
    return {t: load_price_data(t, start, end, market) for t in tickers}


if __name__ == "__main__":
    # Quick manual smoke test (requires internet access to Yahoo Finance / vnstock endpoints)
    df = load_price_data("SPY", "2018-01-01", "2024-12-31", market="us")
    print(df.head())
    print(df.tail())
    print(f"{len(df)} rows loaded")
