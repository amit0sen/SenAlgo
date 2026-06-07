"""
SenAlgo Backtesting Engine
by Amit Kumar Sen

Features:
  - Event-driven backtesting on OHLCV data
  - Python signal engine interface (generate() method)
  - Multi-asset support (NSE/BSE equities, crypto, forex)
  - Metrics: Sharpe, Sortino, Calmar, MaxDD, Win Rate, PF
  - Walk-forward optimization
  - Monte Carlo simulation
  - Position sizing (fixed, ATR-based, Kelly)
"""
from __future__ import annotations
import logging
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Type
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

ANNUALIZE = 252   # trading days per year


# ──────────────────────────────────────────────────────────────────────────────
# Signal interface
# ──────────────────────────────────────────────────────────────────────────────

class SignalEngine:
    """Base class for trading signal engines.

    Subclass and override generate() to implement a strategy.
    """

    name: str = "BaseSignal"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Return a Series of signals aligned with df.index.

        Values: 1 (long), -1 (short), 0 (flat).
        """
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────────────────────
# Result types
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: int       # 1=long, -1=short
    entry_price: float
    exit_price: float
    pnl: float
    pnl_pct: float
    size: float = 1.0


@dataclass
class BacktestMetrics:
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe: float = 0.0
    sortino: float = 0.0
    calmar: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    avg_trade_pnl: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    best_trade: float = 0.0
    worst_trade: float = 0.0
    volatility: float = 0.0
    var_95: float = 0.0

    def to_dict(self) -> dict:
        return {k: round(v, 4) if isinstance(v, float) else v
                for k, v in self.__dict__.items()}


@dataclass
class BacktestResult:
    symbol: str
    engine_name: str
    metrics: BacktestMetrics
    trades: List[Trade]
    equity_curve: pd.Series
    signals: pd.Series
    benchmark_return: float = 0.0
    sharpe_vs_random: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol,
            "engine": self.engine_name,
            "metrics": self.metrics.to_dict(),
            "total_trades": len(self.trades),
            "benchmark_return": round(self.benchmark_return, 4),
            "summary": self.summary,
        }


# ──────────────────────────────────────────────────────────────────────────────
# Backtesting Engine
# ──────────────────────────────────────────────────────────────────────────────

class BacktestEngine:
    """Event-driven backtesting engine."""

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        commission: float = 0.001,      # 0.1% per trade
        slippage: float = 0.001,        # 0.1% slippage
        sizing: str = "fixed",          # "fixed" | "atr" | "kelly"
        risk_per_trade: float = 0.01,   # 1% risk per trade
    ):
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage = slippage
        self.sizing = sizing
        self.risk_per_trade = risk_per_trade

    def run(
        self,
        df: pd.DataFrame,
        engine: SignalEngine,
        symbol: str = "UNKNOWN",
    ) -> BacktestResult:
        """Run backtest for a signal engine on OHLCV data."""
        # Generate signals
        signals = engine.generate(df)
        signals = signals.reindex(df.index).fillna(0)

        # Simulate trades
        trades, equity = self._simulate(df, signals)

        # Metrics
        metrics = self._compute_metrics(equity, trades)

        # Benchmark (buy-and-hold)
        bh_return = (df["close"].iloc[-1] - df["close"].iloc[0]) / df["close"].iloc[0]

        result = BacktestResult(
            symbol=symbol,
            engine_name=engine.name,
            metrics=metrics,
            trades=trades,
            equity_curve=equity,
            signals=signals,
            benchmark_return=bh_return,
        )
        result.summary = self._build_summary(result)
        return result

    def _simulate(
        self, df: pd.DataFrame, signals: pd.Series
    ) -> Tuple[List[Trade], pd.Series]:
        capital = self.initial_capital
        position = 0
        entry_price = 0.0
        entry_time = None
        trades: List[Trade] = []
        equity_values = []

        atr = self._compute_atr(df) if self.sizing == "atr" else None

        for i, (ts, row) in enumerate(df.iterrows()):
            sig = signals.iloc[i] if i < len(signals) else 0
            price = row["close"]

            # Determine position size
            size = self._compute_size(capital, price, atr.iloc[i] if atr is not None else None, i)

            # Close existing position if signal changes
            if position != 0 and sig != position:
                exit_p = price * (1 - self.slippage if position == 1 else 1 + self.slippage)
                pnl = (exit_p - entry_price) * position * size
                pnl -= abs(pnl) * self.commission * 2
                capital += pnl
                trades.append(Trade(
                    entry_time=entry_time,
                    exit_time=ts,
                    direction=position,
                    entry_price=entry_price,
                    exit_price=exit_p,
                    pnl=pnl,
                    pnl_pct=pnl / (entry_price * size),
                    size=size,
                ))
                position = 0

            # Open new position
            if sig != 0 and position == 0:
                entry_price = price * (1 + self.slippage if sig == 1 else 1 - self.slippage)
                entry_time = ts
                position = int(sig)

            equity_values.append(capital)

        equity = pd.Series(equity_values, index=df.index)
        return trades, equity

    def _compute_size(
        self,
        capital: float,
        price: float,
        atr: Optional[float],
        bar_idx: int,
    ) -> float:
        if self.sizing == "atr" and atr and atr > 0:
            risk_amount = capital * self.risk_per_trade
            size = risk_amount / atr
            return max(1.0, size / price)
        elif self.sizing == "kelly":
            # Simplified Kelly: assume 55% win rate, 1:1.5 RR
            f = 0.55 - (0.45 / 1.5)
            return max(0.1, f) * capital / price
        return 1.0  # fixed size

    def _compute_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        tr = pd.concat([
            df["high"] - df["low"],
            (df["high"] - df["close"].shift()).abs(),
            (df["low"] - df["close"].shift()).abs(),
        ], axis=1).max(axis=1)
        return tr.ewm(span=period).mean()

    def _compute_metrics(self, equity: pd.Series, trades: List[Trade]) -> BacktestMetrics:
        if equity.empty or len(equity) < 2:
            return BacktestMetrics()

        returns = equity.pct_change().dropna()
        total_return = (equity.iloc[-1] / equity.iloc[0]) - 1
        n_days = len(equity)
        ann_return = (1 + total_return) ** (ANNUALIZE / n_days) - 1 if n_days > 0 else 0

        # Sharpe
        vol = returns.std() * math.sqrt(ANNUALIZE)
        sharpe = (ann_return / vol) if vol > 0 else 0

        # Sortino
        downside = returns[returns < 0].std() * math.sqrt(ANNUALIZE)
        sortino = (ann_return / downside) if downside > 0 else 0

        # Max drawdown
        rolling_max = equity.cummax()
        drawdown = (equity - rolling_max) / rolling_max
        max_dd = drawdown.min()

        # Drawdown duration
        dd_dur = 0
        cur_dur = 0
        for d in drawdown:
            if d < 0:
                cur_dur += 1
                dd_dur = max(dd_dur, cur_dur)
            else:
                cur_dur = 0

        calmar = (ann_return / abs(max_dd)) if max_dd != 0 else 0

        # Trade stats
        pnls = [t.pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        win_rate = len(wins) / len(pnls) if pnls else 0
        gross_profit = sum(wins)
        gross_loss = abs(sum(losses))
        pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

        # VaR 95%
        var_95 = float(np.percentile(returns, 5)) if len(returns) > 0 else 0

        return BacktestMetrics(
            total_return=total_return,
            annualized_return=ann_return,
            sharpe=sharpe,
            sortino=sortino,
            calmar=calmar,
            max_drawdown=max_dd,
            max_drawdown_duration=dd_dur,
            win_rate=win_rate,
            profit_factor=pf,
            total_trades=len(trades),
            avg_trade_pnl=sum(pnls) / len(pnls) if pnls else 0,
            avg_win=sum(wins) / len(wins) if wins else 0,
            avg_loss=sum(losses) / len(losses) if losses else 0,
            best_trade=max(pnls) if pnls else 0,
            worst_trade=min(pnls) if pnls else 0,
            volatility=vol,
            var_95=var_95,
        )

    def walk_forward(
        self,
        df: pd.DataFrame,
        engine: SignalEngine,
        train_pct: float = 0.6,
        n_splits: int = 5,
        symbol: str = "UNKNOWN",
    ) -> List[BacktestResult]:
        """Walk-forward validation across multiple time windows."""
        results = []
        split_size = len(df) // n_splits
        for i in range(n_splits - 1):
            start = i * split_size
            end = start + split_size + int(split_size * (1 - train_pct))
            window = df.iloc[start:end]
            if len(window) < 30:
                continue
            r = self.run(window, engine, symbol=f"{symbol}_wf{i+1}")
            results.append(r)
        return results

    def monte_carlo(
        self,
        trades: List[Trade],
        n_simulations: int = 1000,
    ) -> Dict:
        """Monte Carlo simulation by shuffling trade order."""
        if not trades:
            return {}
        pnls = [t.pnl for t in trades]
        final_equities = []
        max_dds = []
        for _ in range(n_simulations):
            shuffled = random.sample(pnls, len(pnls))
            eq = self.initial_capital
            equity = []
            for p in shuffled:
                eq += p
                equity.append(eq)
            final_equities.append(equity[-1])
            eq_series = pd.Series(equity)
            rolling_max = eq_series.cummax()
            dd = ((eq_series - rolling_max) / rolling_max).min()
            max_dds.append(float(dd))

        return {
            "mean_final_equity": float(np.mean(final_equities)),
            "p5_final_equity": float(np.percentile(final_equities, 5)),
            "p95_final_equity": float(np.percentile(final_equities, 95)),
            "mean_max_dd": float(np.mean(max_dds)),
            "worst_max_dd": float(np.min(max_dds)),
            "probability_profit": float(np.mean([e > self.initial_capital for e in final_equities])),
        }

    def _build_summary(self, result: BacktestResult) -> str:
        m = result.metrics
        return (
            f"Total Return: {m.total_return:.1%} | "
            f"Sharpe: {m.sharpe:.2f} | "
            f"Max DD: {m.max_drawdown:.1%} | "
            f"Win Rate: {m.win_rate:.1%} | "
            f"Trades: {m.total_trades} | "
            f"vs Buy-Hold: {result.benchmark_return:.1%}"
        )
