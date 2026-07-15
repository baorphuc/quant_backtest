"""
metrics.py
Standard quant performance metrics computed from a daily net_return series.
"""

from __future__ import annotations
import numpy as np
import pandas as pd

TRADING_DAYS = 252


def cagr(equity: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    n_periods = len(equity)
    if n_periods < 2 or equity.iloc[0] <= 0:
        return np.nan
    total_return = equity.iloc[-1] / equity.iloc[0]
    years = n_periods / periods_per_year
    if years <= 0:
        return np.nan
    return total_return ** (1 / years) - 1


def annualized_vol(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    return returns.std() * np.sqrt(periods_per_year)


def sharpe_ratio(returns: pd.Series, risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    excess = returns - risk_free / periods_per_year
    std = excess.std()
    if std == 0 or np.isnan(std):
        return np.nan
    return (excess.mean() / std) * np.sqrt(periods_per_year)


def sortino_ratio(returns: pd.Series, risk_free: float = 0.0, periods_per_year: int = TRADING_DAYS) -> float:
    excess = returns - risk_free / periods_per_year
    downside = excess[excess < 0]
    downside_std = downside.std()
    if downside_std == 0 or np.isnan(downside_std):
        return np.nan
    return (excess.mean() / downside_std) * np.sqrt(periods_per_year)


def max_drawdown(equity: pd.Series) -> float:
    running_max = equity.cummax()
    drawdown = equity / running_max - 1
    return drawdown.min()


def calmar_ratio(equity: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    mdd = max_drawdown(equity)
    if mdd == 0 or np.isnan(mdd):
        return np.nan
    return cagr(equity, periods_per_year) / abs(mdd)


def win_rate(returns: pd.Series) -> float:
    traded = returns[returns != 0]
    if len(traded) == 0:
        return np.nan
    return (traded > 0).mean()


def num_trades(position: pd.Series) -> int:
    return int((position.diff().fillna(0) != 0).sum())


def summarize(backtest_df: pd.DataFrame, label: str = "Strategy") -> dict:
    """
    backtest_df must contain columns: net_return, equity, position
    (as produced by backtest_engine.run_backtest).
    """
    returns = backtest_df["net_return"]
    equity = backtest_df["equity"]
    position = backtest_df["position"]

    return {
        "label": label,
        "CAGR": cagr(equity),
        "AnnVol": annualized_vol(returns),
        "Sharpe": sharpe_ratio(returns),
        "Sortino": sortino_ratio(returns),
        "MaxDrawdown": max_drawdown(equity),
        "Calmar": calmar_ratio(equity),
        "WinRate": win_rate(returns),
        "NumTrades": num_trades(position),
        "FinalEquity": equity.iloc[-1] if len(equity) else np.nan,
    }


def summary_table(results: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(results).set_index("label")
    pct_cols = ["CAGR", "AnnVol", "MaxDrawdown", "WinRate"]
    for c in pct_cols:
        if c in df.columns:
            df[c] = (df[c] * 100).round(2)
    for c in ["Sharpe", "Sortino", "Calmar"]:
        if c in df.columns:
            df[c] = df[c].round(2)
    if "FinalEquity" in df.columns:
        df["FinalEquity"] = df["FinalEquity"].round(0)
    return df
