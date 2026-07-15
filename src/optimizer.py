"""
optimizer.py
Simple grid-search parameter optimization with a chronological train/test
split, to avoid overfitting a single set of parameters to the full history.

This is intentionally simple (not full walk-forward rolling windows) but
demonstrates the core discipline: optimize on train, report on test.
"""

from __future__ import annotations
import itertools
import pandas as pd

from backtest_engine import run_backtest, train_test_split_dates
from metrics import sharpe_ratio


def grid_search(
    df: pd.DataFrame,
    strategy_fn,
    param_grid: dict,
    split_ratio: float = 0.7,
    cost_bps: float = 10.0,
    metric_fn=sharpe_ratio,
) -> dict:
    """
    Parameters
    ----------
    df : full price DataFrame
    strategy_fn : callable(df, **params) -> signal Series
    param_grid : dict of {param_name: [values]}
    split_ratio : train fraction (chronological split)
    metric_fn : function(returns_series) -> float, used to rank on TRAIN

    Returns
    -------
    dict with keys: best_params, train_score, test_score, test_backtest
    """
    train_df, test_df = train_test_split_dates(df, split_ratio)

    keys = list(param_grid.keys())
    combos = list(itertools.product(*param_grid.values()))

    best_params = None
    best_train_score = float("-inf")

    for combo in combos:
        params = dict(zip(keys, combo))
        try:
            signal = strategy_fn(train_df, **params)
            bt = run_backtest(train_df, signal, cost_bps=cost_bps)
            score = metric_fn(bt["net_return"])
        except Exception:
            continue
        if score is not None and score == score and score > best_train_score:  # score==score filters NaN
            best_train_score = score
            best_params = params

    if best_params is None:
        raise RuntimeError("Grid search failed to find valid parameters.")

    # Evaluate best params on untouched test set
    test_signal = strategy_fn(test_df, **best_params)
    test_bt = run_backtest(test_df, test_signal, cost_bps=cost_bps)
    test_score = metric_fn(test_bt["net_return"])

    return {
        "best_params": best_params,
        "train_score": best_train_score,
        "test_score": test_score,
        "test_backtest": test_bt,
        "train_df": train_df,
        "test_df": test_df,
    }
