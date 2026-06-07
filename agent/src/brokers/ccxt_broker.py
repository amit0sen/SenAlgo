"""
CCXT Universal Crypto Broker — SenAlgo by Amit Kumar Sen
Supports 100+ exchanges: Binance, OKX, Bybit, Kraken, Coinbase, etc.
pip install ccxt
"""
from __future__ import annotations
import os
from .base import BrokerBase, Order, Position


class CCXTBroker(BrokerBase):
    """Generic CCXT broker — works with any supported exchange."""

    def __init__(self, exchange_id: str = "okx",
                 api_key: str = "", api_secret: str = "",
                 passphrase: str = "", **kwargs):
        super().__init__(**kwargs)
        self.exchange_id = exchange_id
        self.name = f"ccxt_{exchange_id}"
        self._key = api_key or os.environ.get(f"{exchange_id.upper()}_API_KEY", "")
        self._secret = api_secret or os.environ.get(f"{exchange_id.upper()}_API_SECRET", "")
        self._passphrase = passphrase or os.environ.get(f"{exchange_id.upper()}_PASSPHRASE", "")
        self._exchange = None

    def _get_exchange(self):
        if self._exchange is None:
            import ccxt
            cls = getattr(ccxt, self.exchange_id)
            cfg = {"apiKey": self._key, "secret": self._secret}
            if self._passphrase:
                cfg["password"] = self._passphrase
            self._exchange = cls(cfg)
        return self._exchange

    def get_positions(self) -> list[Position]:
        ex = self._get_exchange()
        balance = ex.fetch_balance()
        positions = []
        for asset, info in balance.get("total", {}).items():
            if info and float(info) > 0:
                positions.append(Position(
                    symbol=asset,
                    quantity=float(info),
                    avg_price=0,
                    current_price=0,
                    pnl=0,
                ))
        return positions

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] {self.exchange_id} order: {order.side} {order.quantity} {order.symbol}"
        ex = self._get_exchange()
        resp = ex.create_order(
            symbol=order.symbol,
            type="market" if order.price is None else "limit",
            side=order.side,
            amount=order.quantity,
            price=order.price,
        )
        return resp.get("id", "")

    def cancel_order(self, order_id: str) -> bool:
        ex = self._get_exchange()
        try:
            ex.cancel_order(order_id)
            return True
        except Exception:
            return False

    def get_quote(self, symbol: str) -> dict:
        ex = self._get_exchange()
        ticker = ex.fetch_ticker(symbol)
        return {"symbol": symbol, "last": ticker.get("last", 0)}
