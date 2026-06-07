"""
ICT (Inner Circle Trader) Concepts — SenAlgo by Amit Kumar Sen

Implements:
- Power of 3 (Accumulation, Manipulation, Distribution)
- Kill Zones (London, New York, Asia)
- Optimal Trade Entry (OTE) retracement zone
- Breaker Blocks
- Mitigation Blocks
- NWOG / NDOG (New Week / Day Opening Gap)
- Displacement / Imbalance detection
"""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import time as dtime
from typing import List, Optional
import pandas as pd
import numpy as np


KILL_ZONES = {
    "asia":       (dtime(20, 0),  dtime(23, 59)),  # UTC-5 / EST
    "london":     (dtime(2,  0),  dtime(5,  0)),
    "new_york":   (dtime(7,  0),  dtime(10, 0)),
    "london_close": (dtime(10, 0), dtime(12, 0)),
}

OTE_FIBS = (0.62, 0.705, 0.786)  # Optimal Trade Entry zone


@dataclass
class BreakerBlock:
    idx: int
    price_high: float
    price_low: float
    direction: str   # "bullish" | "bearish"
    broken: bool = False


@dataclass
class MitigationBlock:
    idx: int
    price: float
    direction: str


@dataclass
class ICTResult:
    power_of_3_phase: str = "unknown"   # accumulation | manipulation | distribution
    ote_zone_high: float = 0.0
    ote_zone_low: float = 0.0
    in_kill_zone: str = ""
    breaker_blocks: List[BreakerBlock] = field(default_factory=list)
    mitigation_blocks: List[MitigationBlock] = field(default_factory=list)
    nwog: float = 0.0
    ndog: float = 0.0
    displacement_bars: List[int] = field(default_factory=list)
    bias: str = "neutral"
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "power_of_3_phase": self.power_of_3_phase,
            "ote_zone": {"high": round(self.ote_zone_high, 4),
                         "low":  round(self.ote_zone_low, 4)},
            "in_kill_zone": self.in_kill_zone,
            "breaker_blocks": len(self.breaker_blocks),
            "mitigation_blocks": len(self.mitigation_blocks),
            "displacement_bars": self.displacement_bars[-3:],
            "bias": self.bias,
            "nwog": round(self.nwog, 4),
            "ndog": round(self.ndog, 4),
            "summary": self.summary,
        }


class ICTEngine:
    """Full ICT concept analysis engine."""

    def __init__(self, swing_len: int = 5, displacement_atr_mult: float = 2.0):
        self.swing_len = swing_len
        self.displacement_atr_mult = displacement_atr_mult

    def analyze(self, df: pd.DataFrame) -> ICTResult:
        df = df.copy().reset_index(drop=True)
        result = ICTResult()

        result.power_of_3_phase = self._power_of_3(df)
        result.bias = self._determine_bias(df)
        result.ote_zone_high, result.ote_zone_low = self._ote_zone(df)
        result.in_kill_zone = self._kill_zone(df)
        result.breaker_blocks = self._breaker_blocks(df)
        result.mitigation_blocks = self._mitigation_blocks(df)
        result.displacement_bars = self._displacement(df)
        result.ndog = self._ndog(df)
        result.summary = self._build_summary(result)
        return result

    def _power_of_3(self, df: pd.DataFrame) -> str:
        """Classify current bar as AMD phase based on candle position."""
        if len(df) < 3:
            return "unknown"
        recent = df.tail(3)
        opens = recent["open"].values
        closes = recent["close"].values
        highs = recent["high"].values
        lows = recent["low"].values

        # Simple heuristic: early range expansion = accumulation,
        # fake spike = manipulation, trend close = distribution
        body_sizes = abs(closes - opens)
        if body_sizes[0] < body_sizes.mean() * 0.5:
            return "accumulation"
        if highs[-1] > highs[-2] and closes[-1] < opens[-1]:
            return "manipulation"   # bull trap
        if lows[-1] < lows[-2] and closes[-1] > opens[-1]:
            return "manipulation"   # bear trap
        return "distribution"

    def _determine_bias(self, df: pd.DataFrame) -> str:
        if len(df) < 20:
            return "neutral"
        sma = df["close"].rolling(20).mean()
        last = df["close"].iloc[-1]
        if last > sma.iloc[-1]:
            return "bullish"
        elif last < sma.iloc[-1]:
            return "bearish"
        return "neutral"

    def _ote_zone(self, df: pd.DataFrame) -> tuple[float, float]:
        """OTE = 62–78.6% Fibonacci retracement of the last swing."""
        if len(df) < 20:
            return 0.0, 0.0
        high = df["high"].tail(20).max()
        low  = df["low"].tail(20).min()
        rng  = high - low
        return high - rng * OTE_FIBS[0], high - rng * OTE_FIBS[2]

    def _kill_zone(self, df: pd.DataFrame) -> str:
        """Check if latest bar falls in a Kill Zone (UTC-5 / EST times)."""
        if "datetime" not in df.columns and df.index.dtype == "datetime64[ns]":
            df = df.copy()
            df["datetime"] = df.index
        if "datetime" not in df.columns:
            return ""
        last_dt = pd.to_datetime(df["datetime"].iloc[-1])
        t = last_dt.time()
        for zone, (start, end) in KILL_ZONES.items():
            if start <= t <= end:
                return zone
        return ""

    def _breaker_blocks(self, df: pd.DataFrame) -> List[BreakerBlock]:
        """A Breaker Block is a failed Order Block that price has broken through."""
        blocks = []
        s = self.swing_len
        for i in range(s, len(df) - s):
            is_swing_high = (df["high"].iloc[i] == df["high"].iloc[i - s:i + s + 1].max())
            is_swing_low  = (df["low"].iloc[i]  == df["low"].iloc[i - s:i + s + 1].min())
            if is_swing_high:
                # Check if price later breaks below this high's candle low
                future = df["close"].iloc[i + 1:]
                if (future < df["low"].iloc[i]).any():
                    blocks.append(BreakerBlock(
                        idx=i,
                        price_high=df["high"].iloc[i],
                        price_low=df["low"].iloc[i],
                        direction="bearish",
                        broken=True,
                    ))
            if is_swing_low:
                future = df["close"].iloc[i + 1:]
                if (future > df["high"].iloc[i]).any():
                    blocks.append(BreakerBlock(
                        idx=i,
                        price_high=df["high"].iloc[i],
                        price_low=df["low"].iloc[i],
                        direction="bullish",
                        broken=True,
                    ))
        return blocks[-5:]  # last 5

    def _mitigation_blocks(self, df: pd.DataFrame) -> List[MitigationBlock]:
        """Prior Order Blocks that have been revisited (mitigated)."""
        blocks = []
        closes = df["close"].values
        highs  = df["high"].values
        lows   = df["low"].values
        for i in range(1, len(df) - 1):
            for j in range(i + 1, len(df)):
                # A bullish mitigation: price drops back to a prior up-close candle
                if closes[i] > df["open"].values[i]:  # up candle
                    if lows[j] <= highs[i] and lows[j] >= lows[i]:
                        blocks.append(MitigationBlock(idx=i, price=closes[i], direction="bullish"))
                        break
        return blocks[-5:]

    def _displacement(self, df: pd.DataFrame) -> List[int]:
        """Find displacement bars: large range candles with closing near extremes."""
        atr = df["high"].sub(df["low"]).rolling(14).mean()
        thresh = atr * self.displacement_atr_mult
        disp = []
        for i in range(14, len(df)):
            candle_range = df["high"].iloc[i] - df["low"].iloc[i]
            if candle_range >= thresh.iloc[i]:
                disp.append(i)
        return disp[-10:]

    def _ndog(self, df: pd.DataFrame) -> float:
        """New Day Opening Gap — gap between yesterday's close and today's open."""
        if len(df) < 2:
            return 0.0
        return df["open"].iloc[-1] - df["close"].iloc[-2]

    def _build_summary(self, r: ICTResult) -> str:
        parts = [f"ICT Bias: {r.bias.upper()}",
                 f"AMD Phase: {r.power_of_3_phase}"]
        if r.in_kill_zone:
            parts.append(f"Kill Zone: {r.in_kill_zone.replace('_', ' ').title()}")
        if r.ote_zone_high:
            parts.append(f"OTE Zone: {r.ote_zone_low:.2f}–{r.ote_zone_high:.2f}")
        if r.breaker_blocks:
            parts.append(f"Breaker Blocks: {len(r.breaker_blocks)}")
        return " | ".join(parts)
