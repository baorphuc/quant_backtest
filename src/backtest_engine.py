"""
backtest_engine.py
Vectorized single-asset backtester.

Key design decisions (explicitly called out because they matter for correctness):
1. NO LOOKAHEAD BIAS: signal[t] is computed from close[t], but the position
   is only APPLIED starting the next bar (signal.shift(1)). This simulates
   "decide at today's close, execute at tomorrow's open/close".
2. TRANSACTION COSTS: applied whenever position changes, as a fraction of
   notional traded (default 10 bps = 0.10%, override as needed).
3. Position sizing here is binary (0/1 or -1/0/1) full-in/full-out. This is
   an MVP; risk-based sizing can be layered on top later.
"""

from __future__ import annotations
import pandas as pd
import numpy as np


def run_backtest(
    df: pd.DataFrame,
    signal: pd.Series,
    cost_bps: float = 10.0,
    initial_capital: float = 100_000.0,
) -> pd.DataFrame:
    """
    Parameters
    ----------
    df : DataFrame with a 'close' column
    signal : Series of target positions in {-1, 0, 1}, indexed like df
    cost_bps : round-trip-agnostic transaction cost in basis points,
               charged on the notional whenever position changes
    initial_capital : starting portfolio value

    Returns
    -------
    DataFrame with columns:
        close, signal, position, market_return, strategy_return,
        cost, net_return, equity, buyhold_equity
    """
    out = pd.DataFrame(index=df.index)
    out["close"] = df["close"]
    out["signal"] = signal.reindex(df.index).fillna(0)

    # Execute next bar to avoid lookahead bias
    out["position"] = out["signal"].shift(1).fillna(0)

    out["market_return"] = out["close"].pct_change().fillna(0)
    out["strategy_return"] = out["position"] * out["market_return"]

    # Transaction cost whenever position changes
    position_change = out["position"].diff().abs().fillna(out["position"].abs())
    out["cost"] = position_change * (cost_bps / 10_000)
    out["net_return"] = out["strategy_return"] - out["cost"]

    out["equity"] = initial_capital * (1 + out["net_return"]).cumprod()
    out["buyhold_equity"] = initial_capital * (1 + out["market_return"]).cumprod()

    return out


def train_test_split_dates(df: pd.DataFrame, split_ratio: float = 0.7):
    """Chronological split — never shuffle time series data."""
    n = len(df)
    split_idx = int(n * split_ratio)
    train = df.iloc[:split_idx]
    test = df.iloc[split_idx:]
    return train, test
