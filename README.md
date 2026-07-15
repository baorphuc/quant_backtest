# Quant Strategy Backtesting Framework

A Python framework for backtesting simple quantitative trading strategies
(SMA Crossover, RSI Mean-Reversion, Bollinger Bands) on historical stock
data — US (S&P 500 via yfinance) or Vietnam (via vnstock) — with proper
attention to lookahead bias, transaction costs, and out-of-sample validation.

## Project Structure

```
quant_backtest/
├── src/
│   ├── data_loader.py      # fetch + cache OHLCV (yfinance / vnstock)
│   ├── strategies.py       # SMA, RSI, Bollinger signal generators
│   ├── backtest_engine.py  # vectorized backtest, next-day execution, costs
│   ├── metrics.py          # Sharpe, Sortino, CAGR, MaxDD, Calmar, WinRate
│   ├── optimizer.py        # grid search with train/test split
│   └── main.py             # CLI entry point, runs full comparison
├── data/                   # cached CSVs (auto-created)
├── outputs/                # summary tables + equity curve plots
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
cd src
python main.py --ticker SPY --market us --start 2015-01-01 --end 2024-12-31
python main.py --ticker FPT --market vn --start 2018-01-01 --end 2024-12-31
```

Outputs a performance summary table and equity-curve plot in `outputs/`.

## Design Notes (why this isn't a naive backtest)

1. **No lookahead bias.** Signals are computed from information available
   at close of day *t*, but `backtest_engine.run_backtest` shifts the
   position by one bar (`signal.shift(1)`) before applying it to returns —
   simulating "decide today, execute tomorrow."

2. **Transaction costs.** Every position change is charged a cost in basis
   points (default 10 bps) on notional traded. Strategies with high churn
   (e.g. Bollinger mean-reversion) will visibly lose edge once costs are
   included — this is realistic and worth discussing in an interview.

3. **Train/test split for parameter selection.** `optimizer.py` performs
   grid search on a chronological train slice and reports performance on
   an untouched test slice, avoiding the classic mistake of tuning
   parameters on the full history and reporting an inflated Sharpe.

4. **Benchmark.** Every comparison includes Buy & Hold — a strategy only
   "works" if it beats a passive baseline on a risk-adjusted basis, not
   just in raw return.

## Metrics Reported

CAGR, Annualized Volatility, Sharpe Ratio, Sortino Ratio, Max Drawdown,
Calmar Ratio, Win Rate, Number of Trades, Final Equity.

## Extending

- **Position sizing:** current sizing is full-in/full-out (0/1). A natural
  extension is ATR-based or volatility-targeted position sizing.
- **Multi-asset:** `data_loader.load_multiple()` already supports fetching
  several tickers; a portfolio-level backtest engine (weights, rebalancing)
  can be layered on top of the single-asset engine.
- **Walk-forward optimization:** `optimizer.py` currently does a single
  train/test split; extending to rolling walk-forward windows is the next
  step for a more rigorous overfitting check.

## CV Line

> Built a Python-based backtesting framework for quantitative trading
> strategies using historical stock data (S&P 500 / VN market). Implemented
> SMA Crossover, RSI, and Bollinger Bands strategies with lookahead-bias-free
> execution and transaction cost modeling; evaluated via Sharpe Ratio, CAGR,
> and Maximum Drawdown against a Buy & Hold benchmark, with train/test
> parameter validation to guard against overfitting.
