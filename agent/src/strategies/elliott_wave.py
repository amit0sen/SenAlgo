"""
Elliott Wave Analyzer — SenAlgo by Amit Kumar Sen

Detects impulse (5-wave) and corrective (3-wave ABC) patterns.
Uses Fibonacci ratios for wave projections and retracements.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np

# Fibonacci ratios
FIB = [0.236, 0.382, 0.500, 0.618, 0.786, 1.000, 1.272, 1.414, 1.618, 2.000, 2.618]

IMPULSE_RULES = {
    "wave2_retracement":     (0.50, 1.00),   # W2 retraces 50–99% of W1
    "wave3_extension_min":   1.618,           # W3 >= 1.618× W1 length
    "wave4_retracement":     (0.24, 0.62),   # W4 retraces 24–62% of W3
    "wave4_no_overlap":      True,            # W4 must not enter W1 territory
    "wave5_extension":       (0.618, 1.618), # W5 = 0.618–1.618× W1
}


@dataclass
class EWave:
    number: int          # 1–5 (impulse) or A/B/C (corrective = 1/2/3)
    wave_type: str       # "impulse" or "corrective"
    start_idx: int
    end_idx: int
    start_price: float
    end_price: float
    direction: str       # "up" / "down"
    fib_level: float = 0.0


@dataclass
class EWavePattern:
    pattern_type: str    # "impulse_5wave" | "corrective_abc" | "unknown"
    waves: List[EWave] = field(default_factory=list)
    degree: str = "minor"   # minor / intermediate / primary / cycle
    valid: bool = False
    violations: List[str] = field(default_factory=list)
    # Projections
    wave3_target: float = 0.0
    wave5_target: float = 0.0
    c_wave_target: float = 0.0
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "pattern_type": self.pattern_type,
            "degree": self.degree,
            "valid": self.valid,
            "violations": self.violations,
            "wave_count": len(self.waves),
            "wave3_target": round(self.wave3_target, 4),
            "wave5_target": round(self.wave5_target, 4),
            "c_wave_target": round(self.c_wave_target, 4),
            "confidence": round(self.confidence, 2),
            "waves": [
                {
                    "number": w.number,
                    "type": w.wave_type,
                    "start": w.start_price,
                    "end": w.end_price,
                    "direction": w.direction,
                }
                for w in self.waves
            ],
        }


class ElliottWaveAnalyzer:
    """Detect Elliott Wave patterns from OHLCV data."""

    def __init__(self, swing_sensitivity: int = 5):
        self.swing_sensitivity = swing_sensitivity

    def analyze(self, df: pd.DataFrame) -> EWavePattern:
        df = df.copy().reset_index(drop=True)
        swings = self._find_swings(df)
        if len(swings) < 6:
            return EWavePattern(pattern_type="unknown", confidence=0.0)

        # Try impulse (5-wave)
        impulse = self._try_impulse(df, swings[-6:])
        if impulse.valid and impulse.confidence > 0.5:
            return impulse

        # Try corrective (ABC)
        if len(swings) >= 4:
            corrective = self._try_corrective(df, swings[-4:])
            if corrective.valid:
                return corrective

        return impulse  # return best guess

    # ------------------------------------------------------------------
    def _find_swings(self, df: pd.DataFrame) -> List[Tuple[int, float, str]]:
        """Find swing highs and lows. Returns (idx, price, 'high'|'low')."""
        s = self.swing_sensitivity
        highs, lows = [], []
        for i in range(s, len(df) - s):
            window_h = df["high"].iloc[i - s:i + s + 1]
            window_l = df["low"].iloc[i - s:i + s + 1]
            if df["high"].iloc[i] == window_h.max():
                highs.append((i, df["high"].iloc[i], "high"))
            if df["low"].iloc[i] == window_l.min():
                lows.append((i, df["low"].iloc[i], "low"))

        # Merge and sort by index, alternating high/low
        all_swings = sorted(highs + lows, key=lambda x: x[0])
        alternating: List[Tuple[int, float, str]] = []
        last_type = None
        for swing in all_swings:
            if swing[2] != last_type:
                alternating.append(swing)
                last_type = swing[2]
        return alternating

    def _try_impulse(self, df: pd.DataFrame,
                     swings: List[Tuple]) -> EWavePattern:
        if len(swings) < 6:
            return EWavePattern(pattern_type="impulse_5wave", valid=False)

        pts = swings[-6:]  # 0=wave-start, 1=W1end, 2=W2end, 3=W3end, 4=W4end, 5=W5end
        prices = [p[1] for p in pts]
        p0, p1, p2, p3, p4, p5 = prices

        up = p1 > p0  # bullish impulse?
        violations = []

        w1 = abs(p1 - p0)
        w2 = abs(p2 - p1)
        w3 = abs(p3 - p2)
        w4 = abs(p4 - p3)
        w5 = abs(p5 - p4)

        # Rule: W2 retracement
        w2_ret = w2 / w1 if w1 > 0 else 0
        if not (0.50 <= w2_ret <= 1.00):
            violations.append(f"W2 retracement {w2_ret:.2f} outside 50-100%")

        # Rule: W3 must be longest of 1,3,5
        if w3 < max(w1, w5) * 0.9:
            violations.append("W3 is not the longest wave")

        # Rule: W3 extension
        w3_ext = w3 / w1 if w1 > 0 else 0
        if w3_ext < 1.618:
            violations.append(f"W3 extension {w3_ext:.2f} < 1.618 minimum")

        # Rule: W4 no overlap with W1
        if up and p4 <= p1:
            violations.append("W4 overlaps W1 top (Elliott Rule violation)")
        elif not up and p4 >= p1:
            violations.append("W4 overlaps W1 bottom (Elliott Rule violation)")

        # Confidence score
        confidence = max(0.0, 1.0 - len(violations) * 0.25)

        # Projections
        w3_target = (p2 + w1 * 1.618) if up else (p2 - w1 * 1.618)
        w5_target = (p4 + w1 * 1.0) if up else (p4 - w1 * 1.0)

        waves = [
            EWave(1, "impulse", pts[0][0], pts[1][0], p0, p1, "up" if up else "down"),
            EWave(2, "impulse", pts[1][0], pts[2][0], p1, p2, "down" if up else "up"),
            EWave(3, "impulse", pts[2][0], pts[3][0], p2, p3, "up" if up else "down"),
            EWave(4, "impulse", pts[3][0], pts[4][0], p3, p4, "down" if up else "up"),
            EWave(5, "impulse", pts[4][0], pts[5][0], p4, p5, "up" if up else "down"),
        ]

        return EWavePattern(
            pattern_type="impulse_5wave",
            waves=waves,
            valid=len(violations) == 0,
            violations=violations,
            wave3_target=round(w3_target, 4),
            wave5_target=round(w5_target, 4),
            confidence=confidence,
        )

    def _try_corrective(self, df: pd.DataFrame,
                        swings: List[Tuple]) -> EWavePattern:
        if len(swings) < 4:
            return EWavePattern(pattern_type="corrective_abc", valid=False)

        pts = swings[-4:]
        prices = [p[1] for p in pts]
        p0, pa, pb, pc = prices

        violations = []
        down = pa < p0  # bearish correction?

        a = abs(pa - p0)
        b = abs(pb - pa)
        c = abs(pc - pb)

        b_ret = b / a if a > 0 else 0
        if not (0.382 <= b_ret <= 0.886):
            violations.append(f"B-wave retracement {b_ret:.2f} outside 38.2-88.6%")

        c_ext = c / a if a > 0 else 0
        if not (0.618 <= c_ext <= 1.618):
            violations.append(f"C-wave extension {c_ext:.2f} outside 61.8-161.8%")

        confidence = max(0.0, 1.0 - len(violations) * 0.3)
        c_target = (pb - a * 1.0) if down else (pb + a * 1.0)

        waves = [
            EWave(1, "corrective", pts[0][0], pts[1][0], p0, pa, "down" if down else "up"),
            EWave(2, "corrective", pts[1][0], pts[2][0], pa, pb, "up" if down else "down"),
            EWave(3, "corrective", pts[2][0], pts[3][0], pb, pc, "down" if down else "up"),
        ]

        return EWavePattern(
            pattern_type="corrective_abc",
            waves=waves,
            valid=len(violations) == 0,
            violations=violations,
            c_wave_target=round(c_target, 4),
            confidence=confidence,
        )
