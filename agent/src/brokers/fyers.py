"""
Fyers Broker Connector — SenAlgo by Amit Kumar Sen
Indian NSE/BSE equities and F&O via Fyers API v3.
Also provides REAL-TIME WebSocket data feed for live tick data.
pip install fyers-apiv3
"""
from __future__ import annotations
import os
import threading
from typing import Callable, Optional
from .base import BrokerBase, Order, Position


class FyersBroker(BrokerBase):
    """Connector for Fyers — trading + real-time data feed."""

    name = "fyers"

    def __init__(self, client_id: str = "", access_token: str = "", **kwargs):
        super().__init__(**kwargs)
        self.client_id = client_id or os.environ.get("FYERS_CLIENT_ID", "")
        self.access_token = access_token or os.environ.get("FYERS_ACCESS_TOKEN", "")
        self._client = None
        self._ws = None

    def _get_client(self):
        if self._client is None:
            from fyers_apiv3 import fyersModel
            self._client = fyersModel.FyersModel(
                client_id=self.client_id,
                is_async=False,
                token=self.access_token,
                log_path="",
            )
        return self._client

    # ------------------------------------------------------------------
    # Real-time data feed via WebSocket
    # ------------------------------------------------------------------
    def start_realtime_feed(
        self,
        symbols: list[str],
        on_tick: Callable[[dict], None],
        data_type: str = "SymbolUpdate",
    ) -> None:
        """
        Start a live WebSocket feed for given symbols.

        symbols   — e.g. ["NSE:RELIANCE-EQ", "NSE:NIFTY50-INDEX"]
        on_tick   — callback called with each tick dict
        data_type — "SymbolUpdate" (LTP) or "DepthUpdate" (order book)
        """
        from fyers_apiv3.FyersWebsocket import data_ws

        def _on_message(msg):
            if isinstance(msg, list):
                for tick in msg:
                    on_tick(tick)
            elif isinstance(msg, dict):
                on_tick(msg)

        def _on_error(err):
            print(f"[Fyers WS Error] {err}")

        def _on_close():
            print("[Fyers WS] Connection closed.")

        self._ws = data_ws.FyersDataSocket(
            access_token=f"{self.client_id}:{self.access_token}",
            log_path="",
            litemode=False,
            write_to_file=False,
            reconnect=True,
            on_connect=lambda: self._ws.subscribe(symbols=symbols, data_type=data_type),
            on_close=_on_close,
            on_error=_on_error,
            on_message=_on_message,
        )
        t = threading.Thread(target=self._ws.connect, daemon=True)
        t.start()

    def stop_realtime_feed(self) -> None:
        if self._ws:
            self._ws.close_connection()
            self._ws = None

    # ------------------------------------------------------------------
    # Trading
    # ------------------------------------------------------------------
    def get_positions(self) -> list[Position]:
        client = self._get_client()
        resp = client.positions()
        positions = []
        for p in resp.get("netPositions", []):
            qty = p.get("netQty", 0)
            if qty != 0:
                positions.append(Position(
                    symbol=p["symbol"],
                    quantity=qty,
                    avg_price=p.get("netAvg", 0),
                    current_price=p.get("ltp", 0),
                    pnl=p.get("pl", 0),
                ))
        return positions

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] Fyers order: {order.side} {order.quantity} {order.symbol} @ {order.price or 'MKT'}"
        client = self._get_client()
        data = {
            "symbol": order.symbol,
            "qty": order.quantity,
            "type": 2 if order.price is None else 1,  # 2=market, 1=limit
            "side": 1 if order.side == "buy" else -1,
            "productType": "INTRADAY",
            "limitPrice": order.price or 0,
            "stopPrice": 0,
            "validity": "DAY",
            "disclosedQty": 0,
            "offlineOrder": False,
        }
        resp = client.place_order(data=data)
        return resp.get("id", "")

    def cancel_order(self, order_id: str) -> bool:
        client = self._get_client()
        resp = client.cancel_order(data={"id": order_id})
        return resp.get("s") == "ok"

    def get_quote(self, symbol: str) -> dict:
        client = self._get_client()
        resp = client.quotes(data={"symbols": symbol})
        d = resp.get("d", [])
        if d:
            ltp = d[0].get("v", {}).get("lp", 0)
            return {"symbol": symbol, "last": ltp}
        return {"symbol": symbol, "last": 0}
