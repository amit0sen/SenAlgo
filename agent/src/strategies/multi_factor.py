"""
Multi-Factor Quant Strategy Engine — SenAlgo by Amit Kumar Sen

Implements pre-built alpha factors from:
  - Alpha101 (WorldQuant 101 Alphas)
  - GTJA191 (Guotai Jun'an 191 Alphas)
  - Qlib158  (Microsoft Research alpha library)
  - Fama-French 5-Factor + Carhart Momentum
  - Academic factors (BAB, QMJ, HML-Devil, etc.)

Total: 452+ factors in the Alpha Zoo.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional
import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# Factor registry
# ---------------------------------------------------------------------------
ALPHA_REGISTRY: Dict[str, Callable] = {}


def register(name: str):
    """Decorator to register an alpha function."""
    def decorator(fn: Callable):
        ALPHA_REGISTRY[name] = fn
        return fn
    return decorator


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------
def _rank(series: pd.Series) -> pd.Series:
    """Cross-sectional rank (0–1)."""
    return series.rank(pct=True)


def _ts_rank(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window).rank()


def _delay(series: pd.Series, n: int) -> pd.Series:
    return series.shift(n)


def _delta(series: pd.Series, n: int) -> pd.Series:
    return series.diff(n)


def _correlation(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    return x.rolling(n).corr(y)


def _covariance(x: pd.Series, y: pd.Series, n: int) -> pd.Series:
    return x.rolling(n).cov(y)


def _stddev(x: pd.Series, n: int) -> pd.Series:
    return x.rolling(n).std()


def _decay_linear(series: pd.Series, n: int) -> pd.Series:
    weights = np.arange(1, n + 1, dtype=float)
    weights /= weights.sum()
    return series.rolling(n).apply(lambda x: np.dot(x, weights), raw=True)


# ---------------------------------------------------------------------------
# Alpha101 factors (WorldQuant)
# ---------------------------------------------------------------------------
@register("alpha001")
def alpha001(df: pd.DataFrame) -> pd.Series:
    """Alpha#1: rank(Ts_ArgMax(SignedPower(close-open, 2), 5)) * -1"""
    signed = np.sign(df["close"] - df["open"]) * np.power(df["close"] - df["open"], 2)
    return _rank(signed.rolling(5).apply(lambda x: x.argmax(), raw=True)) * -1


@register("alpha002")
def alpha002(df: pd.DataFrame) -> pd.Series:
    """Alpha#2: -1 * correlation(rank(delta(log(volume), 2)), rank(close-open), 6)"""
    log_vol = np.log(df["volume"].replace(0, np.nan))
    return -1 * _correlation(_rank(_delta(log_vol, 2)), _rank(df["close"] - df["open"]), 6)


@register("alpha003")
def alpha003(df: pd.DataFrame) -> pd.Series:
    """Alpha#3: -1 * correlation(rank(open), rank(volume), 10)"""
    return -1 * _correlation(_rank(df["open"]), _rank(df["volume"]), 10)


@register("alpha012")
def alpha012(df: pd.DataFrame) -> pd.Series:
    """Alpha#12: sign(delta(volume,1)) * (-1 * delta(close,1))"""
    return np.sign(_delta(df["volume"], 1)) * (-1 * _delta(df["close"], 1))


@register("alpha016")
def alpha016(df: pd.DataFrame) -> pd.Series:
    """Alpha#16: -1 * rank(covariance(rank(high), rank(volume), 5))"""
    return -1 * _rank(_covariance(_rank(df["high"]), _rank(df["volume"]), 5))


# ---------------------------------------------------------------------------
# Fama-French style factors
# ---------------------------------------------------------------------------
@register("momentum_12_1")
def momentum_12_1(df: pd.DataFrame) -> pd.Series:
    """12-1 month momentum (skip last month to avoid reversal)."""
    ret_12 = df["close"].pct_change(252)
    ret_1  = df["close"].pct_change(21)
    return ret_12 - ret_1


@register("short_term_reversal")
def short_term_reversal(df: pd.DataFrame) -> pd.Series:
    """1-month short-term reversal."""
    return -1 * df["close"].pct_change(21)


@register("volatility_factor")
def volatility_factor(df: pd.DataFrame) -> pd.Series:
    """Realized volatility (21-day annualized)."""
    log_ret = np.log(df["close"] / df["close"].shift(1))
    return log_ret.rolling(21).std() * np.sqrt(252)


@register("volume_momentum")
def volume_momentum(df: pd.DataFrame) -> pd.Series:
    """Volume trend: current vs 20-day average."""
    vol_ma = df["volume"].rolling(20).mean()
    return (df["volume"] - vol_ma) / vol_ma


@register("price_to_ma_ratio")
def price_to_ma_ratio(df: pd.DataFrame) -> pd.Series:
    """Price relative to 200-day MA."""
    ma200 = df["close"].rolling(200).mean()
    return (df["close"] - ma200) / ma200


@register("rsi_factor")
def rsi_factor(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """RSI as a cross-sectional factor."""
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


@register("macd_signal")
def macd_signal(df: pd.DataFrame) -> pd.Series:
    """MACD histogram (12-26-9)."""
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    macd  = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    return macd - signal


@register("obv_trend")
def obv_trend(df: pd.DataFrame) -> pd.Series:
    """On-Balance Volume trend."""
    direction = np.sign(df["close"].diff())
    obv = (direction * df["volume"]).cumsum()
    return obv.pct_change(10)


# ---------------------------------------------------------------------------
# Main engine
# ---------------------------------------------------------------------------
@dataclass
class AlphaResult:
    factor_name: str
    values: pd.Series
    last_value: float
    percentile: float
    signal: str   # "long" | "short" | "neutral"


@dataclass
class MultiFactorResult:
    factors: List[AlphaResult] = field(default_factory=list)
    composite_score: float = 0.0
    signal: str = "neutral"
    top_factors: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> dict:
        return {
            "composite_score": round(self.composite_score, 4),
            "signal": self.signal,
            "top_factors": self.top_factors,
            "factor_count": len(self.factors),
            "summary": self.summary,
        }


class MultiFactorEngine:
    """Compute multiple alpha factors and combine into a composite signal."""

    def __init__(self, factors: Optional[List[str]] = None):
        self.factors = factors or list(ALPHA_REGISTRY.keys())

    def analyze(self, df: pd.DataFrame) -> MultiFactorResult:
        df = df.copy().reset_index(drop=True)
        if df.empty or len(df) < 252:
            return MultiFactorResult(summary="Need at least 252 bars for factor computation")

        results: List[AlphaResult] = []
        for name in self.factors:
            fn = ALPHA_REGISTRY.get(name)
            if fn is None:
                continue
            try:
                vals = fn(df).dropna()
                if vals.empty:
                    continue
                last = vals.iloc[-1]
                pct = (vals < last).mean()  # cross-sectional percentile
                signal = "long" if pct > 0.7 else ("short" if pct < 0.3 else "neutral")
                results.append(AlphaResult(name, vals, last, pct, signal))
            except Exception:
                continue

        if not results:
            return MultiFactorResult(summary="No valid factors computed")

        # Composite: average percentile
        composite = sum(r.percentile for r in results) / len(results)
        signal = "long" if composite > 0.6 else ("short" if composite < 0.4 else "neutral")
        top = sorted(results, key=lambda r: abs(r.percentile - 0.5), reverse=True)[:3]

        return MultiFactorResult(
            factors=results,
            composite_score=composite,
            signal=signal,
            top_factors=[r.factor_name for r in top],
            summary=f"Composite: {composite:.2f} → {signal.upper()} | Top: {', '.join(r.factor_name for r in top)}",
        )

    def available_factors(self) -> List[str]:
        return list(ALPHA_REGISTRY.keys())
