"""
SenAlgo SMC Engine — Smart Money Concepts Analysis
by Amit Kumar Sen

Features:
  - Market Structure (BOS / CHOCH)
  - Order Blocks (Internal + Swing)
  - Fair Value Gaps (FVG)
  - Equal Highs / Equal Lows (Liquidity Pools)
  - Premium / Discount Zones
  - Displacement Candles
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class OrderBlock:
    index: int
    timestamp: pd.Timestamp
    top: float
    bottom: float
    bias: int          # 1 = bullish, -1 = bearish
    mitigated: bool = False
    mitigation_idx: Optional[int] = None
    strength: float = 0.0


@dataclass
class FairValueGap:
    index: int
    timestamp: pd.Timestamp
    top: float
    bottom: float
    bias: int          # 1 = bullish (gap up), -1 = bearish (gap down)
    filled: bool = False
    fill_pct: float = 0.0


@dataclass
class StructurePoint:
    index: int
    timestamp: pd.Timestamp
    price: float
    kind: str          # "BOS" | "CHOCH"
    bias: int          # 1 = bullish, -1 = bearish


@dataclass
class LiquidityLevel:
    index: int
    timestamp: pd.Timestamp
    price: float
    kind: str          # "EQH" | "EQL"
    swept: bool = False


@dataclass
class SMCResult:
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fair_value_gaps: List[FairValueGap] = field(default_factory=list)
    structure: List[StructurePoint] = field(default_factory=list)
    liquidity: List[LiquidityLevel] = field(default_factory=list)
    swing_highs: List[int] = field(default_factory=list)
    swing_lows: List[int] = field(default_factory=list)
    premium_zone: Optional[Tuple[float, float]] = None
    discount_zone: Optional[Tuple[float, float]] = None
    equilibrium: Optional[float] = None
    trend: int = 0     # 1 = bullish, -1 = bearish, 0 = neutral
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "order_blocks": len(self.order_blocks),
            "bullish_obs": sum(1 for ob in self.order_blocks if ob.bias == 1 and not ob.mitigated),
            "bearish_obs": sum(1 for ob in self.order_blocks if ob.bias == -1 and not ob.mitigated),
            "fair_value_gaps": len(self.fair_value_gaps),
            "bullish_fvg": sum(1 for f in self.fair_value_gaps if f.bias == 1 and not f.filled),
            "bearish_fvg": sum(1 for f in self.fair_value_gaps if f.bias == -1 and not f.filled),
            "structure_breaks": len(self.structure),
            "liquidity_levels": len(self.liquidity),
            "trend": "bullish" if self.trend == 1 else ("bearish" if self.trend == -1 else "neutral"),
            "equilibrium": self.equilibrium,
            "summary": self.summary,
        }


class SMCEngine:
    """Smart Money Concepts analysis engine."""

    def __init__(self, swing_length: int = 5, ob_size: int = 3, fvg_min_size: float = 0.001):
        self.swing_length = swing_length
        self.ob_size = ob_size
        self.fvg_min_size = fvg_min_size

    def analyze(self, df: pd.DataFrame) -> SMCResult:
        """Run full SMC analysis on OHLCV dataframe.

        Args:
            df: DataFrame with columns: open, high, low, close, volume

        Returns:
            SMCResult with all SMC annotations
        """
        if len(df) < self.swing_length * 2 + 1:
            return SMCResult(summary="Insufficient data for SMC analysis")

        df = df.copy()
        result = SMCResult()

        # 1. Find swing highs and lows
        result.swing_highs, result.swing_lows = self._find_swings(df)

        # 2. Detect market structure (BOS / CHOCH)
        result.structure = self._detect_structure(df, result.swing_highs, result.swing_lows)

        # 3. Determine trend
        result.trend = self._determine_trend(result.structure)

        # 4. Find Order Blocks
        result.order_blocks = self._find_order_blocks(df, result.structure)

        # 5. Detect Fair Value Gaps
        result.fair_value_gaps = self._find_fvgs(df)

        # 6. Find Equal Highs / Equal Lows (Liquidity)
        result.liquidity = self._find_liquidity(df, result.swing_highs, result.swing_lows)

        # 7. Premium / Discount zones
        if result.swing_highs and result.swing_lows:
            recent_high = max(df["high"].iloc[h] for h in result.swing_highs[-3:] if h < len(df))
            recent_low = min(df["low"].iloc[l] for l in result.swing_lows[-3:] if l < len(df))
            mid = (recent_high + recent_low) / 2
            result.equilibrium = mid
            result.premium_zone = (mid, recent_high)
            result.discount_zone = (recent_low, mid)

        # 8. Build summary
        result.summary = self._build_summary(df, result)
        return result

    def _find_swings(self, df: pd.DataFrame) -> Tuple[List[int], List[int]]:
        """Identify swing highs and lows using pivot detection."""
        highs, lows = [], []
        n = self.swing_length
        for i in range(n, len(df) - n):
            window_h = df["high"].iloc[i - n:i + n + 1]
            window_l = df["low"].iloc[i - n:i + n + 1]
            if df["high"].iloc[i] == window_h.max():
                highs.append(i)
            if df["low"].iloc[i] == window_l.min():
                lows.append(i)
        return highs, lows

    def _detect_structure(
        self, df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int]
    ) -> List[StructurePoint]:
        """Detect Break of Structure (BOS) and Change of Character (CHOCH)."""
        structure = []
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return structure

        prev_bias = 0
        prev_high = df["high"].iloc[swing_highs[0]] if swing_highs else 0
        prev_low = df["low"].iloc[swing_lows[0]] if swing_lows else 0

        for i in range(1, min(len(swing_highs), len(swing_lows))):
            sh_idx = swing_highs[i]
            sl_idx = swing_lows[i]
            sh_price = df["high"].iloc[sh_idx]
            sl_price = df["low"].iloc[sl_idx]

            # BOS Bullish: price breaks above previous swing high
            if sh_price > prev_high:
                kind = "CHOCH" if prev_bias == -1 else "BOS"
                structure.append(StructurePoint(
                    index=sh_idx,
                    timestamp=df.index[sh_idx],
                    price=sh_price,
                    kind=kind,
                    bias=1,
                ))
                prev_bias = 1
                prev_high = sh_price

            # BOS Bearish: price breaks below previous swing low
            if sl_price < prev_low:
                kind = "CHOCH" if prev_bias == 1 else "BOS"
                structure.append(StructurePoint(
                    index=sl_idx,
                    timestamp=df.index[sl_idx],
                    price=sl_price,
                    kind=kind,
                    bias=-1,
                ))
                prev_bias = -1
                prev_low = sl_price

            prev_high = max(prev_high, sh_price)
            prev_low = min(prev_low, sl_price)

        return sorted(structure, key=lambda s: s.index)

    def _determine_trend(self, structure: List[StructurePoint]) -> int:
        if not structure:
            return 0
        recent = [s for s in structure[-5:]]
        bull = sum(1 for s in recent if s.bias == 1)
        bear = sum(1 for s in recent if s.bias == -1)
        if bull > bear:
            return 1
        elif bear > bull:
            return -1
        return 0

    def _find_order_blocks(
        self, df: pd.DataFrame, structure: List[StructurePoint]
    ) -> List[OrderBlock]:
        """Find order blocks — last opposite candle before a BOS/CHOCH."""
        obs = []
        for sp in structure:
            # Look back ob_size candles for the impulse candle
            start = max(0, sp.index - self.ob_size * 3)
            end = sp.index

            if sp.bias == 1:  # bullish BOS — find last bearish candle before break
                for j in range(end - 1, start - 1, -1):
                    if df["close"].iloc[j] < df["open"].iloc[j]:  # bearish candle
                        body_size = abs(df["open"].iloc[j] - df["close"].iloc[j])
                        strength = body_size / df["close"].iloc[j]
                        obs.append(OrderBlock(
                            index=j,
                            timestamp=df.index[j],
                            top=df["high"].iloc[j],
                            bottom=df["low"].iloc[j],
                            bias=1,
                            strength=strength,
                        ))
                        break

            elif sp.bias == -1:  # bearish BOS — find last bullish candle before break
                for j in range(end - 1, start - 1, -1):
                    if df["close"].iloc[j] > df["open"].iloc[j]:  # bullish candle
                        body_size = abs(df["close"].iloc[j] - df["open"].iloc[j])
                        strength = body_size / df["close"].iloc[j]
                        obs.append(OrderBlock(
                            index=j,
                            timestamp=df.index[j],
                            top=df["high"].iloc[j],
                            bottom=df["low"].iloc[j],
                            bias=-1,
                            strength=strength,
                        ))
                        break

        # Mark mitigated OBs
        current_price = df["close"].iloc[-1]
        for ob in obs:
            if ob.bias == 1 and current_price < ob.bottom:
                ob.mitigated = True
            elif ob.bias == -1 and current_price > ob.top:
                ob.mitigated = True

        return obs

    def _find_fvgs(self, df: pd.DataFrame) -> List[FairValueGap]:
        """Detect Fair Value Gaps (3-candle pattern)."""
        fvgs = []
        for i in range(1, len(df) - 1):
            prev = df.iloc[i - 1]
            curr = df.iloc[i]
            nxt = df.iloc[i + 1]

            # Bullish FVG: gap between candle[i-1].high and candle[i+1].low
            if nxt["low"] > prev["high"]:
                gap_size = (nxt["low"] - prev["high"]) / prev["high"]
                if gap_size >= self.fvg_min_size:
                    fvg = FairValueGap(
                        index=i,
                        timestamp=df.index[i],
                        top=nxt["low"],
                        bottom=prev["high"],
                        bias=1,
                    )
                    # Check if filled
                    future = df["low"].iloc[i + 1:]
                    filled_mask = future <= fvg.bottom
                    if filled_mask.any():
                        fvg.filled = True
                        fvg.fill_pct = 1.0
                    fvgs.append(fvg)

            # Bearish FVG: gap between candle[i+1].high and candle[i-1].low
            elif prev["low"] > nxt["high"]:
                gap_size = (prev["low"] - nxt["high"]) / nxt["high"]
                if gap_size >= self.fvg_min_size:
                    fvg = FairValueGap(
                        index=i,
                        timestamp=df.index[i],
                        top=prev["low"],
                        bottom=nxt["high"],
                        bias=-1,
                    )
                    future = df["high"].iloc[i + 1:]
                    filled_mask = future >= fvg.top
                    if filled_mask.any():
                        fvg.filled = True
                        fvg.fill_pct = 1.0
                    fvgs.append(fvg)

        return fvgs

    def _find_liquidity(
        self, df: pd.DataFrame, swing_highs: List[int], swing_lows: List[int]
    ) -> List[LiquidityLevel]:
        """Find Equal Highs (EQH) and Equal Lows (EQL) — liquidity pools."""
        levels = []
        tolerance = 0.001  # 0.1% tolerance for "equal"

        # Equal Highs
        sh_prices = [(i, df["high"].iloc[i]) for i in swing_highs]
        for a in range(len(sh_prices)):
            for b in range(a + 1, len(sh_prices)):
                ia, pa = sh_prices[a]
                ib, pb = sh_prices[b]
                if abs(pa - pb) / pa < tolerance:
                    levels.append(LiquidityLevel(
                        index=ib,
                        timestamp=df.index[ib],
                        price=(pa + pb) / 2,
                        kind="EQH",
                    ))

        # Equal Lows
        sl_prices = [(i, df["low"].iloc[i]) for i in swing_lows]
        for a in range(len(sl_prices)):
            for b in range(a + 1, len(sl_prices)):
                ia, pa = sl_prices[a]
                ib, pb = sl_prices[b]
                if abs(pa - pb) / pa < tolerance:
                    levels.append(LiquidityLevel(
                        index=ib,
                        timestamp=df.index[ib],
                        price=(pa + pb) / 2,
                        kind="EQL",
                    ))

        # Mark swept levels
        current_high = df["high"].iloc[-1]
        current_low = df["low"].iloc[-1]
        for lvl in levels:
            if lvl.kind == "EQH" and current_high > lvl.price:
                lvl.swept = True
            elif lvl.kind == "EQL" and current_low < lvl.price:
                lvl.swept = True

        return levels

    def _build_summary(self, df: pd.DataFrame, result: SMCResult) -> str:
        trend_str = {1: "BULLISH", -1: "BEARISH", 0: "NEUTRAL"}.get(result.trend, "NEUTRAL")
        price = df["close"].iloc[-1]
        active_bull_ob = sum(1 for ob in result.order_blocks if ob.bias == 1 and not ob.mitigated)
        active_bear_ob = sum(1 for ob in result.order_blocks if ob.bias == -1 and not ob.mitigated)
        open_fvg = sum(1 for f in result.fair_value_gaps if not f.filled)
        recent_bos = [s for s in result.structure[-3:] if s.kind == "BOS"]
        recent_choch = [s for s in result.structure[-3:] if s.kind == "CHOCH"]
        zone = ""
        if result.premium_zone and result.discount_zone:
            if price > result.equilibrium:
                zone = "PREMIUM (look for shorts / distribution)"
            else:
                zone = "DISCOUNT (look for longs / accumulation)"

        parts = [
            f"Market trend: {trend_str}",
            f"Current price: {price:.2f}",
            f"Price zone: {zone}",
            f"Active Order Blocks: {active_bull_ob} bullish, {active_bear_ob} bearish",
            f"Open FVGs: {open_fvg}",
            f"Recent BOS: {len(recent_bos)}, CHOCH: {len(recent_choch)}",
            f"Liquidity levels: {len(result.liquidity)} ({sum(1 for l in result.liquidity if not l.swept)} unswept)",
        ]
        return " | ".join(parts)
