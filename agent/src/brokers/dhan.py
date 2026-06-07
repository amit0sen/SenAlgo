"""
Dhan Broker Connector — SenAlgo by Amit Kumar Sen
Indian NSE/BSE equities and F&O via Dhan API.
pip install dhanhq
"""
from __future__ import annotations
import os
from typing import Optional
from .base import BrokerBase, Order, Position


class DhanBroker(BrokerBase):
    """Connector for Dhan (dhanhq library)."""

    name = "dhan"

    def __init__(self, client_id: str = "", access_token: str = "", **kwargs):
        super().__init__(**kwargs)
        self.client_id = client_id or os.environ.get("DHAN_CLIENT_ID", "")
        self.access_token = access_token or os.environ.get("DHAN_ACCESS_TOKEN", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from dhanhq import dhanhq
            self._client = dhanhq(self.client_id, self.access_token)
        return self._client

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        raw = client.get_positions()
        positions = []
        for p in raw.get("data", []):
            if p.get("netQty", 0) != 0:
                positions.append(Position(
                    symbol=p["tradingSymbol"],
                    quantity=p["netQty"],
                    avg_price=p["buyAvg"],
                    current_price=p["lastTradedPrice"],
                    pnl=p["unrealizedProfit"],
                ))
        return positions

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] Dhan order: {order.side} {order.quantity} {order.symbol} @ {order.price or 'MKT'}"
        client = self._get_client()
        from dhanhq import dhanhq
        resp = client.place_order(
            security_id=order.symbol,
            exchange_segment=dhanhq.NSE,
            transaction_type=dhanhq.BUY if order.side == "buy" else dhanhq.SELL,
            quantity=order.quantity,
            order_type=dhanhq.MARKET if order.price is None else dhanhq.LIMIT,
            price=order.price or 0,
            product_type=dhanhq.INTRA,
        )
        return str(resp.get("orderId", ""))

    def cancel_order(self, order_id: str) -> bool:
        client = self._get_client()
        resp = client.cancel_order(order_id)
        return resp.get("status") == "success"

    def get_quote(self, symbol: str) -> dict:
        client = self._get_client()
        resp = client.get_ltp_data(securities={"NSE_EQ": [symbol]})
        data = resp.get("data", {})
        if data:
            row = list(data.values())[0]
            return {"symbol": symbol, "last": row.get("last_price", 0)}
        return {"symbol": symbol, "last": 0}
