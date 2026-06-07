"""
SenAlgo Order Flow Engine
by Amit Kumar Sen

Features:
  - Footprint chart analysis (bid/ask volume per price level)
  - Delta (buy vol - sell vol) per bar
  - Cumulative Delta trend
  - Absorption detection
  - Imbalance detection (stacked imbalances)
  - POC from order flow data
"""
from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class FootprintBar:
    timestamp: pd.Timestamp
    open: float
    high: float
    low: float
    close: float
    volume: float
    delta: float            # buy_vol - sell_vol
    buy_volume: float
    sell_volume: float
    poc: float              # price level with max volume in this bar
    imbalances: List[float] = field(default_factory=list)
    absorption: bool = False


@dataclass
class OrderFlowResult:
    footprint: List[FootprintBar] = field(default_factory=list)
    cumulative_delta: pd.Series = field(default_factory=pd.Series)
    delta_divergence: bool = False   # price up but delta down (or vice versa)
    absorption_zones: List[pd.Timestamp] = field(default_factory=list)
    imbalance_zones: List[pd.Timestamp] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        if not self.footprint:
            return {"summary": self.summary}
        last = self.footprint[-1]
        return {
            "last_delta": last.delta,
            "last_buy_vol": last.buy_volume,
            "last_sell_vol": last.sell_volume,
            "cumulative_delta": float(self.cumulative_delta.iloc[-1]) if len(self.cumulative_delta) else 0,
            "delta_divergence": self.delta_divergence,
            "absorption_zones": len(self.absorption_zones),
            "imbalance_zones": len(self.imbalance_zones),
            "summary": self.summary,
        }


class OrderFlowEngine:
    """Order flow analysis from OHLCV data (estimated) or tick data."""

    IMBALANCE_RATIO = 3.0   # buy/sell ratio threshold for imbalance detection
    ABSORPTION_THRESHOLD = 0.85  # delta/volume ratio for absorption

    def analyze(self, df: pd.DataFrame) -> OrderFlowResult:
        """Analyze order flow from OHLCV DataFrame.

        When real tick data is unavailable, estimates buy/sell split using
        the Tick Rule (close > open → more buys) with volume distribution.
        """
        result = OrderFlowResult()
        result.footprint = self._build_footprint(df)

        if not result.footprint:
            result.summary = "Insufficient data"
            return result

        deltas = pd.Series(
            [bar.delta for bar in result.footprint],
            index=[bar.timestamp for bar in result.footprint],
        )
        result.cumulative_delta = deltas.cumsum()

        # Detect delta divergence (price trending opposite to delta)
        prices = df["close"].values[-10:]
        recent_deltas = [b.delta for b in result.footprint[-10:]]
        if len(prices) >= 5 and len(recent_deltas) >= 5:
            price_trend = np.polyfit(range(len(prices)), prices, 1)[0]
            delta_trend = np.polyfit(range(len(recent_deltas)), recent_deltas, 1)[0]
            result.delta_divergence = (price_trend > 0 and delta_trend < 0) or \
                                       (price_trend < 0 and delta_trend > 0)

        # Absorption and imbalance zones
        result.absorption_zones = [b.timestamp for b in result.footprint if b.absorption]
        result.imbalance_zones = [b.timestamp for b in result.footprint if b.imbalances]
        result.summary = self._build_summary(df, result)
        return result

    def _build_footprint(self, df: pd.DataFrame) -> List[FootprintBar]:
        bars = []
        for i, (ts, row) in enumerate(df.iterrows()):
            vol = row["volume"]
            close = row["close"]
            open_ = row["open"]

            # Estimate buy/sell split using tick rule + candle body
            body_pct = (close - open_) / (row["high"] - row["low"] + 1e-9)
            buy_ratio = max(0.1, min(0.9, 0.5 + body_pct * 0.4))
            buy_vol = vol * buy_ratio
            sell_vol = vol * (1 - buy_ratio)
            delta = buy_vol - sell_vol

            # POC = midpoint of largest body
            poc = (close + open_) / 2

            # Detect absorption: large volume, small delta → both sides absorbing
            absorption = False
            if vol > 0:
                delta_ratio = abs(delta) / vol
                absorption = delta_ratio < (1 - self.ABSORPTION_THRESHOLD)

            # Imbalances: look for consecutive candles with skewed delta
            imbalances = []
            if i > 0:
                prev_buy_ratio = bars[-1].buy_volume / (bars[-1].volume + 1e-9)
                curr_buy_ratio = buy_vol / (vol + 1e-9)
                if curr_buy_ratio / (1 - curr_buy_ratio + 1e-9) > self.IMBALANCE_RATIO:
                    imbalances.append(close)   # bullish imbalance
                elif (1 - curr_buy_ratio) / (curr_buy_ratio + 1e-9) > self.IMBALANCE_RATIO:
                    imbalances.append(close)   # bearish imbalance

            bars.append(FootprintBar(
                timestamp=ts,
                open=open_,
                high=row["high"],
                low=row["low"],
                close=close,
                volume=vol,
                delta=delta,
                buy_volume=buy_vol,
                sell_volume=sell_vol,
                poc=poc,
                imbalances=imbalances,
                absorption=absorption,
            ))
        return bars

    def _build_summary(self, df: pd.DataFrame, result: OrderFlowResult) -> str:
        if not result.footprint:
            return "No footprint data"
        last = result.footprint[-1]
        cd = float(result.cumulative_delta.iloc[-1])
        parts = [
            f"Last bar delta: {last.delta:+.0f} (buy {last.buy_volume:.0f} / sell {last.sell_volume:.0f})",
            f"Cumulative delta: {cd:+,.0f}",
            f"Delta divergence: {'YES — watch for reversal' if result.delta_divergence else 'No'}",
            f"Absorption zones: {len(result.absorption_zones)}",
            f"Imbalance zones: {len(result.imbalance_zones)}",
        ]
        if cd > 0:
            parts.append("Overall: BUYING pressure dominant")
        else:
            parts.append("Overall: SELLING pressure dominant")
        return " | ".join(parts)
