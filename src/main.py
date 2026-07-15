"""
main.py
End-to-end pipeline: load data -> run strategies -> backtest -> compare -> plot.

Run:
    python main.py --ticker SPY --market us --start 2015-01-01 --end 2024-12-31
"""

from __future__ import annotations
import argparse
import os
import pandas as pd
import matplotlib.pyplot as plt

from data_loader import load_price_data
from strategies import sma_crossover, rsi_strategy, bollinger_strategy
from backtest_engine import run_backtest
from metrics import summarize, summary_table

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def run_all_strategies(df: pd.DataFrame, cost_bps: float = 10.0):
    strategies = {
        "SMA_Crossover": sma_crossover(df, fast=20, slow=50),
        "RSI_MeanReversion": rsi_strategy(df, period=14, lower=30, upper=70),
        "Bollinger_MeanReversion": bollinger_strategy(df, window=20, num_std=2.0),
    }

    backtests = {}
    results = []
    for name, signal in strategies.items():
        bt = run_backtest(df, signal, cost_bps=cost_bps)
        backtests[name] = bt
        results.append(summarize(bt, label=name))

    # Buy & hold benchmark (position always 1, no rebalancing cost after entry)
    buyhold_signal = pd.Series(1, index=df.index)
    buyhold_bt = run_backtest(df, buyhold_signal, cost_bps=cost_bps)
    backtests["BuyAndHold"] = buyhold_bt
    results.append(summarize(buyhold_bt, label="BuyAndHold"))

    return backtests, summary_table(results)


def plot_equity_curves(backtests: dict, ticker: str, save_path: str):
    plt.figure(figsize=(11, 6))
    for name, bt in backtests.items():
        plt.plot(bt.index, bt["equity"], label=name, linewidth=1.6)
    plt.title(f"Equity Curves — {ticker}")
    plt.xlabel("Date")
    plt.ylabel("Portfolio Value")
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150)
    plt.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ticker", default="SPY")
    parser.add_argument("--market", default="us", choices=["us", "vn"])
    parser.add_argument("--start", default="2015-01-01")
    parser.add_argument("--end", default="2024-12-31")
    parser.add_argument("--cost_bps", type=float, default=10.0)
    args = parser.parse_args()

    df = load_price_data(args.ticker, args.start, args.end, market=args.market)
    print(f"Loaded {len(df)} rows for {args.ticker} ({args.market}) "
          f"from {df.index.min().date()} to {df.index.max().date()}")

    backtests, table = run_all_strategies(df, cost_bps=args.cost_bps)

    print("\n=== Performance Summary (CAGR%, AnnVol%, Sharpe, Sortino, MaxDD%, Calmar, WinRate%, NumTrades) ===")
    print(table.to_string())

    table.to_csv(os.path.join(OUTPUT_DIR, f"{args.ticker}_summary.csv"))
    plot_path = os.path.join(OUTPUT_DIR, f"{args.ticker}_equity_curves.png")
    plot_equity_curves(backtests, args.ticker, plot_path)
    print(f"\nSaved summary table and equity curve plot to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
