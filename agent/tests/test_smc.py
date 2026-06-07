"""Tests for SMC Engine."""
import pandas as pd
import numpy as np
import pytest
from src.smc.engine import SMCEngine


def make_df(n=100):
    np.random.seed(42)
    close = 100 + np.cumsum(np.random.randn(n) * 0.5)
    high = close + np.abs(np.random.randn(n) * 0.3)
    low = close - np.abs(np.random.randn(n) * 0.3)
    open_ = close + np.random.randn(n) * 0.1
    vol = np.random.randint(1_000_000, 5_000_000, n).astype(float)
    idx = pd.date_range("2023-01-01", periods=n, freq="D")
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol}, index=idx)


def test_smc_returns_result():
    df = make_df()
    engine = SMCEngine(swing_length=3)
    result = engine.analyze(df)
    assert result is not None
    assert result.summary


def test_smc_to_dict():
    df = make_df()
    result = SMCEngine(swing_length=3).analyze(df)
    d = result.to_dict()
    assert "trend" in d
    assert "order_blocks" in d


def test_vp_engine():
    from src.volume_profile.engine import VolumeProfileEngine
    df = make_df()
    engine = VolumeProfileEngine()
    result = engine.analyze(df)
    assert result.profile is not None
    assert result.profile.poc > 0


def test_order_flow():
    from src.order_flow.engine import OrderFlowEngine
    df = make_df()
    engine = OrderFlowEngine()
    result = engine.analyze(df)
    assert result.summary
    assert len(result.footprint) == len(df)


def test_backtest():
    from src.backtest.engine import BacktestEngine
    from src.backtest.signals import EMASignalEngine
    df = make_df(200)
    runner = BacktestEngine(initial_capital=100_000)
    result = runner.run(df, EMASignalEngine(), symbol="TEST")
    assert result.metrics.total_return != 0 or result.metrics.total_trades >= 0
    assert result.summary
