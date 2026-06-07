"""
SenAlgo built-in signal engines
by Amit Kumar Sen
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from src.backtest.engine import SignalEngine
from src.smc.engine import SMCEngine
from src.volume_profile.engine import VolumeProfileEngine


class SMCSignalEngine(SignalEngine):
    """Signal engine based on Smart Money Concepts.

    Long when: price in discount zone + bullish OB nearby + BOS bullish
    Short when: price in premium zone + bearish OB nearby + BOS bearish
    """
    name = "SMC"

    def __init__(self, swing_length: int = 5):
        self.smc = SMCEngine(swing_length=swing_length)

    def generate(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index)
        window = 50
        for i in range(window, len(df)):
            sub = df.iloc[i - window:i]
            try:
                result = self.smc.analyze(sub)
                price = df["close"].iloc[i]
                if result.trend == 1 and result.discount_zone:
                    if result.discount_zone[0] <= price <= result.discount_zone[1]:
                        if any(ob.bias == 1 and not ob.mitigated for ob in result.order_blocks):
                            signals.iloc[i] = 1
                elif result.trend == -1 and result.premium_zone:
                    if result.premium_zone[0] <= price <= result.premium_zone[1]:
                        if any(ob.bias == -1 and not ob.mitigated for ob in result.order_blocks):
                            signals.iloc[i] = -1
            except Exception:
                pass
        return signals


class VWAPRevertSignalEngine(SignalEngine):
    """Mean-reversion to VWAP with volume confirmation."""
    name = "VWAP_Revert"

    def __init__(self, std_threshold: float = 2.0):
        self.vpe = VolumeProfileEngine()
        self.std_threshold = std_threshold

    def generate(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index)
        result = self.vpe.compute_vwap(df)
        close = df["close"]
        upper = result.upper2
        lower = result.lower2
        for i in range(1, len(df)):
            if close.iloc[i] < lower.iloc[i] and close.iloc[i - 1] >= lower.iloc[i - 1]:
                signals.iloc[i] = 1   # bounce from lower band → long
            elif close.iloc[i] > upper.iloc[i] and close.iloc[i - 1] <= upper.iloc[i - 1]:
                signals.iloc[i] = -1  # rejection from upper band → short
            elif abs(close.iloc[i] - result.vwap.iloc[i]) < abs(close.iloc[i - 1] - result.vwap.iloc[i - 1]):
                # returning to VWAP — flatten
                signals.iloc[i] = 0
        return signals


class ORBSignalEngine(SignalEngine):
    """Opening Range Breakout strategy.

    For intraday data: define range from first N bars, trade breakout.
    """
    name = "ORB"

    def __init__(self, orb_bars: int = 3):
        self.orb_bars = orb_bars

    def generate(self, df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(0, index=df.index)
        if len(df) <= self.orb_bars:
            return signals
        orb_high = df["high"].iloc[:self.orb_bars].max()
        orb_low = df["low"].iloc[:self.orb_bars].min()
        in_trade = 0
        for i in range(self.orb_bars, len(df)):
            price = df["close"].iloc[i]
            if in_trade == 0:
                if price > orb_high:
                    signals.iloc[i] = 1
                    in_trade = 1
                elif price < orb_low:
                    signals.iloc[i] = -1
                    in_trade = -1
            else:
                # Exit if price returns to range mid
                mid = (orb_high + orb_low) / 2
                if (in_trade == 1 and price < mid) or (in_trade == -1 and price > mid):
                    signals.iloc[i] = 0
                    in_trade = 0
                else:
                    signals.iloc[i] = in_trade
        return signals


class EMASignalEngine(SignalEngine):
    """Classic EMA crossover as baseline comparison."""
    name = "EMA_Cross"

    def __init__(self, fast: int = 9, slow: int = 21):
        self.fast = fast
        self.slow = slow

    def generate(self, df: pd.DataFrame) -> pd.Series:
        ema_fast = df["close"].ewm(span=self.fast).mean()
        ema_slow = df["close"].ewm(span=self.slow).mean()
        signals = pd.Series(0, index=df.index)
        signals[ema_fast > ema_slow] = 1
        signals[ema_fast < ema_slow] = -1
        return signals


# Registry of built-in engines
BUILT_IN_ENGINES = {
    "smc": SMCSignalEngine,
    "vwap_revert": VWAPRevertSignalEngine,
    "orb": ORBSignalEngine,
    "ema_cross": EMASignalEngine,
}
