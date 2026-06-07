"""
Interactive Brokers Connector — SenAlgo by Amit Kumar Sen
Global equities, options, futures, forex via IBKR TWS/Gateway.
pip install ib_insync
"""
from __future__ import annotations
import os
from .base import BrokerBase, Order, Position


class IBKRBroker(BrokerBase):
    name = "ibkr"

    def __init__(self, host: str = "127.0.0.1", port: int = 7497,
                 client_id: int = 1, **kwargs):
        super().__init__(**kwargs)
        self.host = host or os.environ.get("IBKR_HOST", "127.0.0.1")
        self.port = port or int(os.environ.get("IBKR_PORT", "7497"))
        self.client_id = client_id
        self._ib = None

    def _get_ib(self):
        if self._ib is None:
            from ib_insync import IB
            self._ib = IB()
            self._ib.connect(self.host, self.port, clientId=self.client_id)
        return self._ib

    def get_positions(self) -> list[Position]:
        ib = self._get_ib()
        positions = []
        for pos in ib.positions():
            positions.append(Position(
                symbol=pos.contract.symbol,
                quantity=pos.position,
                avg_price=pos.avgCost,
                current_price=0,
                pnl=0,
            ))
        return positions

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] IBKR order: {order.side} {order.quantity} {order.symbol}"
        from ib_insync import Stock, MarketOrder, LimitOrder
        ib = self._get_ib()
        contract = Stock(order.symbol, "SMART", "USD")
        ib_order = (MarketOrder(order.side.upper(), order.quantity)
                    if order.price is None
                    else LimitOrder(order.side.upper(), order.quantity, order.price))
        trade = ib.placeOrder(contract, ib_order)
        return str(trade.order.orderId)

    def cancel_order(self, order_id: str) -> bool:
        ib = self._get_ib()
        for trade in ib.openTrades():
            if str(trade.order.orderId) == order_id:
                ib.cancelOrder(trade.order)
                return True
        return False

    def get_quote(self, symbol: str) -> dict:
        from ib_insync import Stock
        ib = self._get_ib()
        contract = Stock(symbol, "SMART", "USD")
        ticker = ib.reqMktData(contract, "", True, False)
        ib.sleep(1)
        return {"symbol": symbol, "last": ticker.last or 0}
