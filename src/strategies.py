"""
strategies.py
Vectorized signal generators. Each function takes a price DataFrame
(columns: open, high, low, close, volume) and returns a pd.Series of
target positions in {-1, 0, 1} (or {0, 1} for long-only), indexed the
same as the input.

Convention: signal[t] is decided using information available AT THE
CLOSE of day t. The backtest engine is responsible for shifting this
by one day before applying it to returns, to avoid lookahead bias.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def sma_crossover(df: pd.DataFrame, fast: int = 20, slow: int = 50, long_only: bool = True) -> pd.Series:
    """
    Long when fast SMA > slow SMA, flat/short otherwise.
    """
    fast_ma = df["close"].rolling(fast).mean()
    slow_ma = df["close"].rolling(slow).mean()
    signal = np.where(fast_ma > slow_ma, 1, -1)
    signal = pd.Series(signal, index=df.index, name="signal")
    if long_only:
        signal = signal.clip(lower=0)
    signal[fast_ma.isna() | slow_ma.isna()] = 0
    return signal


def rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Wilder's RSI, returned as a raw indicator series (0-100), not a position."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi_val = 100 - (100 / (1 + rs))
    return rsi_val.rename("rsi")


def rsi_strategy(df: pd.DataFrame, period: int = 14, lower: int = 30, upper: int = 70,
                  long_only: bool = True) -> pd.Series:
    """
    Mean-reversion RSI strategy:
    - Enter long when RSI crosses below `lower` (oversold)
    - Exit / go flat (or short) when RSI crosses above `upper` (overbought)
    - Hold position between signals (stateful, so implemented with a loop-free forward-fill trick).
    """
    r = rsi(df, period)
    raw = pd.Series(np.nan, index=df.index)
    raw[r < lower] = 1
    raw[r > upper] = 0 if long_only else -1
    signal = raw.ffill().fillna(0)
    signal.name = "signal"
    return signal


def bollinger_bands(df: pd.DataFrame, window: int = 20, num_std: float = 2.0):
    """Returns (mid, upper, lower) bands."""
    mid = df["close"].rolling(window).mean()
    std = df["close"].rolling(window).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return mid, upper, lower


def bollinger_strategy(df: pd.DataFrame, window: int = 20, num_std: float = 2.0,
                        long_only: bool = True) -> pd.Series:
    """
    Mean-reversion Bollinger strategy:
    - Enter long when close crosses below the lower band
    - Exit when close crosses back above the middle band (or above upper band -> optionally short)
    """
    mid, upper, lower = bollinger_bands(df, window, num_std)
    close = df["close"]

    raw = pd.Series(np.nan, index=df.index)
    raw[close < lower] = 1
    raw[close > mid] = 0 if long_only else -1
    signal = raw.ffill().fillna(0)
    signal.name = "signal"
    return signal


STRATEGY_REGISTRY = {
    "sma_crossover": sma_crossover,
    "rsi": rsi_strategy,
    "bollinger": bollinger_strategy,
}
