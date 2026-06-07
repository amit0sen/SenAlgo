"""
Tiger Brokers Connector — SenAlgo by Amit Kumar Sen
US/HK/SG equities via Tiger Open API.
pip install tigeropen
"""
from __future__ import annotations
import os
from .base import BrokerBase, Order, Position


class TigerBroker(BrokerBase):
    name = "tiger"

    def __init__(self, tiger_id: str = "", private_key: str = "",
                 account: str = "", **kwargs):
        super().__init__(**kwargs)
        self.tiger_id = tiger_id or os.environ.get("TIGER_ID", "")
        self.private_key = private_key or os.environ.get("TIGER_PRIVATE_KEY", "")
        self.account = account or os.environ.get("TIGER_ACCOUNT", "")
        self._client = None

    def _get_client(self):
        if self._client is None:
            from tigeropen.tiger_open_config import TigerOpenClientConfig
            from tigeropen.trade.trade_client import TradeClient
            config = TigerOpenClientConfig()
            config.tiger_id = self.tiger_id
            config.private_key = self.private_key
            config.account = self.account
            self._client = TradeClient(config)
        return self._client

    def get_positions(self) -> list[Position]:
        client = self._get_client()
        raw = client.get_positions(account=self.account)
        return [
            Position(
                symbol=p.contract.symbol,
                quantity=p.quantity,
                avg_price=p.average_cost,
                current_price=p.market_price,
                pnl=p.unrealized_pnl,
            )
            for p in (raw or [])
        ]

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] Tiger order: {order.side} {order.quantity} {order.symbol}"
        from tigeropen.common.consts import OrderType
        client = self._get_client()
        resp = client.place_order(
            account=self.account,
            symbol=order.symbol,
            action=order.side.upper(),
            quantity=order.quantity,
            order_type=OrderType.MKT if order.price is None else OrderType.LMT,
            limit_price=order.price,
        )
        return str(resp)

    def cancel_order(self, order_id: str) -> bool:
        client = self._get_client()
        try:
            client.cancel_order(account=self.account, id=int(order_id))
            return True
        except Exception:
            return False

    def get_quote(self, symbol: str) -> dict:
        from tigeropen.quote.quote_client import QuoteClient
        from tigeropen.tiger_open_config import TigerOpenClientConfig
        config = TigerOpenClientConfig()
        config.tiger_id = self.tiger_id
        config.private_key = self.private_key
        qc = QuoteClient(config)
        tickers = qc.get_trade_ticks(symbols=[symbol])
        if tickers:
            return {"symbol": symbol, "last": tickers[0].price}
        return {"symbol": symbol, "last": 0}
