"""
SenAlgo Volume Profile Engine
by Amit Kumar Sen

Features:
  - Session / Visible Range / Fixed Range Volume Profile
  - Point of Control (POC), Value Area High (VAH), Value Area Low (VAL)
  - VWAP + Standard Deviation bands
  - Market Profile (TPO)
  - Delta Analysis (buy vs sell volume)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class VolumeProfileResult:
    poc: float                          # Point of Control
    vah: float                          # Value Area High (70%)
    val: float                          # Value Area Low (70%)
    volume_by_price: Dict[float, float] # price_level -> volume
    value_area_pct: float = 0.70
    high: float = 0.0
    low: float = 0.0
    total_volume: float = 0.0

    def is_in_value_area(self, price: float) -> bool:
        return self.val <= price <= self.vah


@dataclass
class VWAPResult:
    vwap: pd.Series
    upper1: pd.Series   # +1 std
    lower1: pd.Series   # -1 std
    upper2: pd.Series   # +2 std
    lower2: pd.Series   # -2 std
    upper3: pd.Series   # +3 std
    lower3: pd.Series   # -3 std


@dataclass
class VolumeAnalysisResult:
    profile: Optional[VolumeProfileResult] = None
    vwap: Optional[VWAPResult] = None
    delta: Optional[pd.Series] = None
    cumulative_delta: Optional[pd.Series] = None
    summary: str = ""

    def to_dict(self) -> dict:
        result = {}
        if self.profile:
            result.update({
                "poc": self.profile.poc,
                "vah": self.profile.vah,
                "val": self.profile.val,
                "total_volume": self.profile.total_volume,
            })
        if self.vwap is not None:
            result["vwap_latest"] = float(self.vwap.vwap.iloc[-1])
        if self.cumulative_delta is not None:
            result["cumulative_delta"] = float(self.cumulative_delta.iloc[-1])
        result["summary"] = self.summary
        return result


class VolumeProfileEngine:
    """Volume profile and VWAP analysis engine."""

    def __init__(self, num_bins: int = 100, value_area_pct: float = 0.70):
        self.num_bins = num_bins
        self.value_area_pct = value_area_pct

    def analyze(self, df: pd.DataFrame) -> VolumeAnalysisResult:
        """Full volume analysis: profile + VWAP + delta."""
        result = VolumeAnalysisResult()
        result.profile = self.compute_volume_profile(df)
        result.vwap = self.compute_vwap(df)

        # Estimate delta if we have intraday data
        if "delta" in df.columns:
            result.delta = df["delta"]
            result.cumulative_delta = df["delta"].cumsum()
        else:
            # Estimate delta from close vs open
            estimated_delta = df.apply(
                lambda row: row["volume"] if row["close"] >= row["open"] else -row["volume"],
                axis=1
            )
            result.delta = estimated_delta
            result.cumulative_delta = estimated_delta.cumsum()

        result.summary = self._build_summary(df, result)
        return result

    def compute_volume_profile(self, df: pd.DataFrame) -> VolumeProfileResult:
        """Compute volume profile: distribution of volume by price level."""
        price_high = df["high"].max()
        price_low = df["low"].min()
        price_range = price_high - price_low

        if price_range == 0:
            return VolumeProfileResult(
                poc=price_high, vah=price_high, val=price_low,
                volume_by_price={price_high: df["volume"].sum()}
            )

        bin_size = price_range / self.num_bins
        bins = np.arange(price_low, price_high + bin_size, bin_size)
        volume_by_price: Dict[float, float] = {round(b, 6): 0.0 for b in bins}

        for _, row in df.iterrows():
            candle_range = row["high"] - row["low"]
            if candle_range == 0:
                continue
            for b in bins:
                overlap_low = max(b, row["low"])
                overlap_high = min(b + bin_size, row["high"])
                if overlap_high > overlap_low:
                    portion = (overlap_high - overlap_low) / candle_range
                    volume_by_price[round(b, 6)] += row["volume"] * portion

        # POC = price level with highest volume
        poc_price = max(volume_by_price, key=volume_by_price.get)
        total_vol = sum(volume_by_price.values())

        # Value Area: 70% of total volume around POC
        sorted_prices = sorted(volume_by_price.items(), key=lambda x: x[1], reverse=True)
        target_vol = total_vol * self.value_area_pct
        accum = 0.0
        va_prices = []
        for price, vol in sorted_prices:
            accum += vol
            va_prices.append(price)
            if accum >= target_vol:
                break

        vah = max(va_prices) + bin_size
        val = min(va_prices)

        return VolumeProfileResult(
            poc=poc_price + bin_size / 2,
            vah=vah,
            val=val,
            volume_by_price=volume_by_price,
            value_area_pct=self.value_area_pct,
            high=price_high,
            low=price_low,
            total_volume=total_vol,
        )

    def compute_vwap(self, df: pd.DataFrame) -> VWAPResult:
        """Compute VWAP with standard deviation bands."""
        typical = (df["high"] + df["low"] + df["close"]) / 3
        cum_vol = df["volume"].cumsum()
        cum_tpv = (typical * df["volume"]).cumsum()
        vwap = cum_tpv / cum_vol

        # Rolling variance for bands
        variance = ((typical - vwap) ** 2 * df["volume"]).cumsum() / cum_vol
        std = np.sqrt(variance)

        return VWAPResult(
            vwap=vwap,
            upper1=vwap + std,
            lower1=vwap - std,
            upper2=vwap + 2 * std,
            lower2=vwap - 2 * std,
            upper3=vwap + 3 * std,
            lower3=vwap - 3 * std,
        )

    def _build_summary(self, df: pd.DataFrame, result: VolumeAnalysisResult) -> str:
        price = df["close"].iloc[-1]
        parts = []
        if result.profile:
            p = result.profile
            parts.append(f"POC: {p.poc:.2f} | VAH: {p.vah:.2f} | VAL: {p.val:.2f}")
            if price > p.vah:
                parts.append("Price ABOVE value area (extended/premium)")
            elif price < p.val:
                parts.append("Price BELOW value area (oversold/discount)")
            else:
                parts.append("Price INSIDE value area")
        if result.vwap:
            vwap_val = float(result.vwap.vwap.iloc[-1])
            parts.append(f"VWAP: {vwap_val:.2f} ({'above' if price > vwap_val else 'below'})")
        if result.cumulative_delta is not None:
            cd = float(result.cumulative_delta.iloc[-1])
            parts.append(f"Cumulative Delta: {cd:+,.0f} ({'buying pressure' if cd > 0 else 'selling pressure'})")
        return " | ".join(parts)
