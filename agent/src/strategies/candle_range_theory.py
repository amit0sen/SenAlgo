"""
Candle Range Theory (CRT) — SenAlgo by Amit Kumar Sen

The three phases on any higher-timeframe candle:
  1. FORMING  — The candle body is being built (initial direction)
  2. RAID     — Price sweeps the opposing side's liquidity (manipulation)
  3. FILL     — Price returns and closes back inside the candle range

This is the intra-candle manipulation model: smart money grabs stops
before moving in the true direction.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import pandas as pd
import numpy as np


@dataclass
class CRTBar:
    idx: int
    open: float
    high: float
    low: float
    close: float
    phase: str            # "forming" | "raid_high" | "raid_low" | "fill" | "complete"
    raid_direction: str   # "high_raid" | "low_raid" | "none"
    fill_complete: bool = False
    setup_valid: bool = False
    entry_direction: str = ""  # expected move after fill: "bullish" | "bearish"


@dataclass
class CRTResult:
    bars: List[CRTBar] = field(default_factory=list)
    active_setup: bool = False
    setup_direction: str = ""   # "bullish" | "bearish"
    raid_level: float = 0.0
    entry_zone_high: float = 0.0
    entry_zone_low: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    risk_reward: float = 0.0
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "active_setup": self.active_setup,
            "setup_direction": self.setup_direction,
            "raid_level": round(self.raid_level, 4),
            "entry_zone": {
                "high": round(self.entry_zone_high, 4),
                "low":  round(self.entry_zone_low, 4),
            },
            "stop_loss": round(self.stop_loss, 4),
            "take_profit": round(self.take_profit, 4),
            "risk_reward": round(self.risk_reward, 2),
            "setup_count": len([b for b in self.bars if b.setup_valid]),
            "summary": self.summary,
        }


class CRTEngine:
    """Candle Range Theory analyzer."""

    def __init__(self, htf_period: int = 4, raid_threshold: float = 0.003):
        """
        htf_period      — how many lower-TF bars make one HTF candle
        raid_threshold  — minimum % beyond prior range to count as a raid
        """
        self.htf_period = htf_period
        self.raid_threshold = raid_threshold

    def analyze(self, df: pd.DataFrame) -> CRTResult:
        df = df.copy().reset_index(drop=True)
        result = CRTResult()

        # Aggregate into HTF candles
        htf = self._aggregate(df)
        if len(htf) < 3:
            result.summary = "Not enough bars for CRT analysis"
            return result

        crt_bars: List[CRTBar] = []
        for i in range(1, len(htf) - 1):
            bar = htf.iloc[i]
            prev = htf.iloc[i - 1]
            crt = self._classify(i, bar, prev)
            crt_bars.append(crt)

        result.bars = crt_bars
        # Find most recent valid setup
        valid = [b for b in crt_bars if b.setup_valid]
        if valid:
            latest = valid[-1]
            result.active_setup = True
            result.setup_direction = latest.entry_direction
            result.raid_level = latest.high if latest.raid_direction == "high_raid" else latest.low
            # Entry zone is the original candle's 50% area
            mid = (latest.high + latest.low) / 2
            result.entry_zone_high = mid + (latest.high - latest.low) * 0.15
            result.entry_zone_low  = mid - (latest.high - latest.low) * 0.15
            if latest.entry_direction == "bullish":
                result.stop_loss   = latest.low * 0.998
                result.take_profit = latest.high + (latest.high - latest.low)
            else:
                result.stop_loss   = latest.high * 1.002
                result.take_profit = latest.low - (latest.high - latest.low)
            rr_risk = abs(result.entry_zone_low - result.stop_loss)
            rr_reward = abs(result.take_profit - result.entry_zone_high)
            result.risk_reward = (rr_reward / rr_risk) if rr_risk > 0 else 0

        result.summary = self._build_summary(result)
        return result

    def _aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        n = self.htf_period
        records = []
        for i in range(0, len(df) - n + 1, n):
            chunk = df.iloc[i:i + n]
            records.append({
                "open":  chunk["open"].iloc[0],
                "high":  chunk["high"].max(),
                "low":   chunk["low"].min(),
                "close": chunk["close"].iloc[-1],
                "volume": chunk["volume"].sum() if "volume" in chunk.columns else 0,
            })
        return pd.DataFrame(records)

    def _classify(self, idx: int, bar: pd.Series, prev: pd.Series) -> CRTBar:
        prev_high = prev["high"]
        prev_low  = prev["low"]
        threshold = (prev_high - prev_low) * self.raid_threshold

        raid_dir = "none"
        if bar["high"] > prev_high + threshold and bar["close"] < prev_high:
            raid_dir = "high_raid"
        elif bar["low"] < prev_low - threshold and bar["close"] > prev_low:
            raid_dir = "low_raid"

        setup_valid = raid_dir != "none"
        entry_dir = ""
        if raid_dir == "high_raid":
            entry_dir = "bearish"  # swept highs → expect drop
        elif raid_dir == "low_raid":
            entry_dir = "bullish"  # swept lows → expect rally

        phase = "complete" if setup_valid else "forming"

        return CRTBar(
            idx=idx,
            open=bar["open"],
            high=bar["high"],
            low=bar["low"],
            close=bar["close"],
            phase=phase,
            raid_direction=raid_dir,
            fill_complete=bar["close"] > prev_low and bar["close"] < prev_high,
            setup_valid=setup_valid,
            entry_direction=entry_dir,
        )

    def _build_summary(self, r: CRTResult) -> str:
        if not r.active_setup:
            return "No active CRT setup detected"
        return (f"CRT {r.setup_direction.upper()} setup | "
                f"Raid @ {r.raid_level:.2f} | "
                f"Entry {r.entry_zone_low:.2f}–{r.entry_zone_high:.2f} | "
                f"R:R {r.risk_reward:.1f}")
