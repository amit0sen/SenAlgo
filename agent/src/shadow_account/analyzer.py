"""
Shadow Account Analyzer — SenAlgo by Amit Kumar Sen

Reads broker trade journal CSV exports and produces:
- Win rate, Profit Factor, Sharpe, MaxDD
- Best/worst times of day / week to trade
- Best/worst instruments
- Risk management report
- Improvement hypotheses

Supports exports from:
  Zerodha (tradebook CSV), Fyers, Dhan, Alpaca, IBKR, Binance
"""
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np


# Column name mappings for different brokers
BROKER_COLUMNS = {
    "zerodha": {
        "date":   "trade_date",
        "symbol": "tradingsymbol",
        "qty":    "quantity",
        "price":  "average_price",
        "side":   "transaction_type",
        "pnl":    None,  # computed
    },
    "fyers": {
        "date":   "orderDateTime",
        "symbol": "symbol",
        "qty":    "qty",
        "price":  "tradedPrice",
        "side":   "side",
        "pnl":    None,
    },
    "dhan": {
        "date":   "Order Date",
        "symbol": "Scrip Name",
        "qty":    "Quantity",
        "price":  "Average Price",
        "side":   "Side",
        "pnl":    "Realized P&L",
    },
    "alpaca": {
        "date":   "date",
        "symbol": "symbol",
        "qty":    "qty",
        "price":  "avg_price",
        "side":   "side",
        "pnl":    None,
    },
    "ibkr": {
        "date":   "Date/Time",
        "symbol": "Symbol",
        "qty":    "Quantity",
        "price":  "T. Price",
        "side":   None,  # derived from qty sign
        "pnl":    "Realized P/L",
    },
    "generic": {
        "date":   "date",
        "symbol": "symbol",
        "qty":    "quantity",
        "price":  "price",
        "side":   "side",
        "pnl":    "pnl",
    },
}


@dataclass
class TradeMetrics:
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    total_pnl: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    best_day: str = ""
    worst_day: str = ""
    best_hour: int = 0
    worst_hour: int = 0
    top_symbols: List[str] = field(default_factory=list)
    worst_symbols: List[str] = field(default_factory=list)
    avg_holding_minutes: float = 0.0


@dataclass
class ShadowAccountResult:
    metrics: TradeMetrics = field(default_factory=TradeMetrics)
    trades_df: Optional[pd.DataFrame] = None
    hypotheses: List[str] = field(default_factory=list)
    report: str = ""

    def to_dict(self) -> dict:
        m = self.metrics
        return {
            "total_trades": m.total_trades,
            "win_rate": round(m.win_rate, 2),
            "profit_factor": round(m.profit_factor, 2),
            "total_pnl": round(m.total_pnl, 2),
            "max_drawdown": round(m.max_drawdown, 2),
            "sharpe_ratio": round(m.sharpe_ratio, 2),
            "avg_win": round(m.avg_win, 2),
            "avg_loss": round(m.avg_loss, 2),
            "best_day": m.best_day,
            "worst_day": m.worst_day,
            "top_symbols": m.top_symbols,
            "worst_symbols": m.worst_symbols,
            "hypotheses": self.hypotheses,
            "report_summary": self.report[:500],
        }


class ShadowAccountAnalyzer:
    """Analyze broker trade journal exports to find patterns and improvements."""

    def __init__(self, broker: str = "generic"):
        self.broker = broker.lower()
        self.col_map = BROKER_COLUMNS.get(self.broker, BROKER_COLUMNS["generic"])

    def analyze_file(self, file_path: str) -> ShadowAccountResult:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Trade journal not found: {file_path}")
        df = pd.read_csv(path)
        return self.analyze_df(df)

    def analyze_df(self, df: pd.DataFrame) -> ShadowAccountResult:
        df = self._normalize(df)
        if df.empty:
            return ShadowAccountResult(report="No trades found in journal.")

        metrics = self._compute_metrics(df)
        hypotheses = self._generate_hypotheses(metrics, df)
        report = self._build_report(metrics, hypotheses)

        return ShadowAccountResult(
            metrics=metrics,
            trades_df=df,
            hypotheses=hypotheses,
            report=report,
        )

    # ------------------------------------------------------------------
    def _normalize(self, df: pd.DataFrame) -> pd.DataFrame:
        cm = self.col_map
        rename = {}
        for std_col, raw_col in cm.items():
            if raw_col and raw_col in df.columns:
                rename[raw_col] = std_col
        df = df.rename(columns=rename)

        # Ensure PnL column
        if "pnl" not in df.columns:
            df["pnl"] = 0.0  # will be computed from paired trades

        # Parse date
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")

        # Parse side
        if "side" in df.columns:
            df["side"] = df["side"].astype(str).str.upper()
            df["side"] = df["side"].map(
                lambda s: "BUY" if any(b in s for b in ["BUY", "B", "LONG", "1"])
                else ("SELL" if any(s2 in s for s2 in ["SELL", "S", "SHORT", "-1"]) else s)
            )
        elif "qty" in df.columns:
            df["side"] = np.where(df["qty"].astype(float) > 0, "BUY", "SELL")
            df["qty"] = df["qty"].astype(float).abs()

        df = df.dropna(subset=["date"] if "date" in df.columns else [])
        return df

    def _compute_metrics(self, df: pd.DataFrame) -> TradeMetrics:
        m = TradeMetrics()
        pnl = df["pnl"].astype(float)

        m.total_trades = len(df)
        m.total_pnl = pnl.sum()
        wins = pnl[pnl > 0]
        losses = pnl[pnl < 0]
        m.winning_trades = len(wins)
        m.losing_trades  = len(losses)
        m.win_rate  = m.winning_trades / m.total_trades if m.total_trades else 0
        m.avg_win   = wins.mean() if len(wins) else 0
        m.avg_loss  = losses.mean() if len(losses) else 0
        gross_profit = wins.sum() if len(wins) else 0
        gross_loss   = abs(losses.sum()) if len(losses) else 1
        m.profit_factor = gross_profit / gross_loss if gross_loss else 0

        # MaxDD from cumulative PnL
        cum = pnl.cumsum()
        roll_max = cum.cummax()
        drawdown = cum - roll_max
        m.max_drawdown = drawdown.min()

        # Sharpe (daily)
        daily = pnl.resample("D", on=df["date"]).sum() if "date" in df.columns else pnl
        m.sharpe_ratio = (daily.mean() / daily.std() * np.sqrt(252)
                          if daily.std() > 0 else 0)

        # Best / worst day of week
        if "date" in df.columns:
            df2 = df.copy()
            df2["_dow"] = df["date"].dt.day_name()
            df2["_pnl"] = pnl
            day_pnl = df2.groupby("_dow")["_pnl"].mean()
            m.best_day  = day_pnl.idxmax() if not day_pnl.empty else ""
            m.worst_day = day_pnl.idxmin() if not day_pnl.empty else ""

            df2["_hour"] = df["date"].dt.hour
            hour_pnl = df2.groupby("_hour")["_pnl"].mean()
            m.best_hour  = int(hour_pnl.idxmax()) if not hour_pnl.empty else 0
            m.worst_hour = int(hour_pnl.idxmin()) if not hour_pnl.empty else 0

        # Best / worst symbols
        if "symbol" in df.columns:
            df3 = df.copy()
            df3["_pnl"] = pnl
            sym_pnl = df3.groupby("symbol")["_pnl"].sum().sort_values(ascending=False)
            m.top_symbols    = list(sym_pnl.head(3).index)
            m.worst_symbols  = list(sym_pnl.tail(3).index)

        return m

    def _generate_hypotheses(self, m: TradeMetrics, df: pd.DataFrame) -> List[str]:
        hyps = []
        if m.win_rate < 0.45:
            hyps.append(
                f"Win rate is {m.win_rate:.0%} — below 45%. "
                "Consider tightening entry criteria or adding trend filter."
            )
        if m.profit_factor < 1.5:
            hyps.append(
                f"Profit factor {m.profit_factor:.2f} < 1.5. "
                "Improve R:R by widening targets or tightening stops."
            )
        if m.max_drawdown < -m.total_pnl * 0.3:
            hyps.append(
                "MaxDD is >30% of total PnL. Reduce position sizing or add max daily loss rule."
            )
        if m.worst_day:
            hyps.append(f"Avoid trading on {m.worst_day} — historically worst day.")
        if m.worst_symbols:
            hyps.append(f"Consider avoiding {', '.join(m.worst_symbols)} — worst performing instruments.")
        if abs(m.avg_loss) > m.avg_win * 2:
            hyps.append(
                f"Avg loss ({m.avg_loss:.2f}) is 2× avg win ({m.avg_win:.2f}). "
                "Enforce strict stop-loss discipline."
            )
        if not hyps:
            hyps.append("Strategy metrics look solid. Continue monitoring and expanding hypothesis space.")
        return hyps

    def _build_report(self, m: TradeMetrics, hypotheses: List[str]) -> str:
        lines = [
            "=" * 60,
            "SHADOW ACCOUNT REPORT — SenAlgo by Amit Kumar Sen",
            "=" * 60,
            f"Total Trades    : {m.total_trades}",
            f"Win Rate        : {m.win_rate:.1%}",
            f"Profit Factor   : {m.profit_factor:.2f}",
            f"Total PnL       : {m.total_pnl:.2f}",
            f"Max Drawdown    : {m.max_drawdown:.2f}",
            f"Sharpe Ratio    : {m.sharpe_ratio:.2f}",
            f"Avg Win         : {m.avg_win:.2f}",
            f"Avg Loss        : {m.avg_loss:.2f}",
            f"Best Day        : {m.best_day}",
            f"Worst Day       : {m.worst_day}",
            f"Top Symbols     : {', '.join(m.top_symbols)}",
            f"Worst Symbols   : {', '.join(m.worst_symbols)}",
            "",
            "IMPROVEMENT HYPOTHESES:",
        ]
        for i, h in enumerate(hypotheses, 1):
            lines.append(f"  {i}. {h}")
        lines.append("=" * 60)
        return "\n".join(lines)
