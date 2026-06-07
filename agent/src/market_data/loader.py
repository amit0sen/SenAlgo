"""SenAlgo market data loaders — yfinance, NSE, CCXT."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def load_ohlcv(
    symbol: str,
    interval: str = "1d",
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = None,
    source: str = "yfinance",
) -> pd.DataFrame:
    """Load OHLCV data for a symbol.

    Args:
        symbol: Ticker (e.g. 'RELIANCE.NS', 'BTC-USDT', 'AAPL')
        interval: '1m','5m','15m','30m','1h','4h','1d','1wk','1mo'
        start: ISO date string YYYY-MM-DD
        end: ISO date string YYYY-MM-DD
        period: yfinance period string ('1y', '6mo', 'max', etc.)
        source: 'yfinance' | 'ccxt' | 'akshare'

    Returns:
        DataFrame with columns: open, high, low, close, volume
    """
    if source == "yfinance" or _is_equity(symbol):
        return _load_yfinance(symbol, interval, start, end, period)
    elif source == "ccxt" or _is_crypto(symbol):
        return _load_ccxt(symbol, interval, start, end)
    else:
        return _load_yfinance(symbol, interval, start, end, period)


def _is_equity(symbol: str) -> bool:
    return any(symbol.endswith(s) for s in [".NS", ".BO", ".BSE"])


def _is_crypto(symbol: str) -> bool:
    return "/" in symbol or "-USDT" in symbol or "-USD" in symbol


def _load_yfinance(
    symbol: str,
    interval: str,
    start: Optional[str],
    end: Optional[str],
    period: Optional[str],
) -> pd.DataFrame:
    import yfinance as yf

    ticker = yf.Ticker(symbol)
    if period:
        df = ticker.history(period=period, interval=interval)
    else:
        df = ticker.history(start=start, end=end, interval=interval)

    if df.empty:
        logger.warning("No data returned for %s", symbol)
        return pd.DataFrame()

    df.columns = [c.lower() for c in df.columns]
    df = df[["open", "high", "low", "close", "volume"]].copy()
    df.index = pd.to_datetime(df.index)
    if df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df.dropna()
    return df


def _load_ccxt(
    symbol: str,
    interval: str,
    start: Optional[str],
    end: Optional[str],
) -> pd.DataFrame:
    try:
        import ccxt
    except ImportError:
        raise ImportError("ccxt not installed. pip install ccxt")

    # map interval to ccxt timeframe
    tf_map = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
              "1h": "1h", "4h": "4h", "1d": "1d", "1wk": "1w"}
    tf = tf_map.get(interval, "1d")

    exchange = ccxt.binance({"enableRateLimit": True})
    since = None
    if start:
        since = int(datetime.fromisoformat(start).timestamp() * 1000)

    ohlcv = exchange.fetch_ohlcv(symbol, tf, since=since, limit=1000)
    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df = df.set_index("timestamp")
    return df


def load_nse_index(symbol: str = "^NSEI", period: str = "1y") -> pd.DataFrame:
    """Load NSE index data (Nifty 50 = ^NSEI, Bank Nifty = ^NSEBANK)."""
    return _load_yfinance(symbol, "1d", None, None, period)


# ---------------------------------------------------------------------------
# Fyers real-time data feed
# ---------------------------------------------------------------------------

class FyersLiveFeed:
    """
    Real-time NSE/BSE tick data via Fyers WebSocket API.

    Usage:
        feed = FyersLiveFeed()
        feed.start(["NSE:RELIANCE-EQ", "NSE:NIFTY50-INDEX"], on_tick=print)
    """

    def __init__(self, client_id: str = "", access_token: str = ""):
        import os
        self.client_id    = client_id    or os.environ.get("FYERS_CLIENT_ID", "")
        self.access_token = access_token or os.environ.get("FYERS_ACCESS_TOKEN", "")
        self._ws = None

    def start(
        self,
        symbols: list[str],
        on_tick,
        data_type: str = "SymbolUpdate",
    ) -> None:
        """
        Start streaming live ticks.

        symbols   — Fyers format: ["NSE:RELIANCE-EQ", "NSE:NIFTY50-INDEX", "MCX:GOLD25JUNFUT"]
        on_tick   — callback(tick: dict)
        data_type — "SymbolUpdate" (LTP) | "DepthUpdate" (full L2 order book)
        """
        from fyers_apiv3.FyersWebsocket import data_ws

        def _on_message(msg):
            if isinstance(msg, list):
                for tick in msg:
                    on_tick(tick)
            elif isinstance(msg, dict):
                on_tick(msg)

        self._ws = data_ws.FyersDataSocket(
            access_token=f"{self.client_id}:{self.access_token}",
            log_path="",
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_connect=lambda: self._ws.subscribe(symbols=symbols, data_type=data_type),
            on_close=lambda: print("[Fyers] Feed closed"),
            on_error=lambda e: print(f"[Fyers] Error: {e}"),
            on_message=_on_message,
        )
        import threading
        t = threading.Thread(target=self._ws.connect, daemon=True)
        t.start()
        print(f"[Fyers] Live feed started for {len(symbols)} symbols")

    def stop(self) -> None:
        if self._ws:
            self._ws.close_connection()
            self._ws = None
            print("[Fyers] Live feed stopped")
