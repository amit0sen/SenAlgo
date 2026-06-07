"""Zerodha Kite broker connector for SenAlgo by Amit Kumar Sen."""
from __future__ import annotations
import logging
import os
from typing import Dict, List, Optional
from src.brokers.base import BrokerBase, Mandate, Order, Position

logger = logging.getLogger(__name__)


class ZerodhaBroker(BrokerBase):
    """Zerodha Kite Connect broker connector.

    Supports NSE/BSE equities and F&O (paper + live).
    Set KITE_API_KEY, KITE_API_SECRET, KITE_ACCESS_TOKEN in env.
    """
    name = "Zerodha"

    def __init__(self, mandate: Optional[Mandate] = None, paper: bool = True):
        super().__init__(mandate=mandate)
        self.paper_only = paper
        self._kite = None
        if not paper:
            self._connect()

    def _connect(self):
        try:
            from kiteconnect import KiteConnect
            api_key = os.environ["KITE_API_KEY"]
            access_token = os.environ["KITE_ACCESS_TOKEN"]
            self._kite = KiteConnect(api_key=api_key)
            self._kite.set_access_token(access_token)
            logger.info("Zerodha Kite connected")
        except ImportError:
            raise ImportError("pip install kiteconnect")
        except KeyError as e:
            raise EnvironmentError(f"Missing env var: {e}")

    def _execute_order(self, order: Order) -> Dict:
        if not self._kite:
            raise RuntimeError("Kite not connected")
        from kiteconnect import KiteConnect
        exchange = "NSE"
        if order.symbol.endswith(".BO"):
            exchange = "BSE"
        order_id = self._kite.place_order(
            variety=KiteConnect.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=order.symbol.replace(".NS", "").replace(".BO", ""),
            transaction_type=KiteConnect.TRANSACTION_TYPE_BUY if order.side == "buy" else KiteConnect.TRANSACTION_TYPE_SELL,
            quantity=int(order.qty),
            product=KiteConnect.PRODUCT_CNC,
            order_type=KiteConnect.ORDER_TYPE_MARKET if order.order_type == "market" else KiteConnect.ORDER_TYPE_LIMIT,
            price=order.price,
        )
        return {"status": "placed", "order_id": order_id}

    def get_positions(self) -> List[Position]:
        if self.paper_only or not self._kite:
            return []
        pos_data = self._kite.positions()
        result = []
        for p in pos_data.get("net", []):
            result.append(Position(
                symbol=p["tradingsymbol"],
                qty=p["quantity"],
                avg_price=p["average_price"],
                current_price=p["last_price"],
                pnl=p["pnl"],
                pnl_pct=p["pnl"] / (p["average_price"] * abs(p["quantity"]) + 1e-9),
            ))
        return result

    def get_account(self) -> Dict:
        if self.paper_only or not self._kite:
            return {"broker": "Zerodha", "mode": "paper", "balance": 0}
        margins = self._kite.margins()
        return {
            "broker": "Zerodha",
            "equity_available": margins["equity"]["available"]["live_balance"],
            "used_margin": margins["equity"]["utilised"]["debits"],
        }

    def _get_price(self, symbol: str) -> float:
        if not self._kite:
            return 0.0
        clean = symbol.replace(".NS", "").replace(".BO", "")
        exchange = "BSE" if symbol.endswith(".BO") else "NSE"
        quote = self._kite.quote([f"{exchange}:{clean}"])
        return quote.get(f"{exchange}:{clean}", {}).get("last_price", 0.0)


class AlpacaBroker(BrokerBase):
    """Alpaca broker connector (US equities)."""
    name = "Alpaca"

    def __init__(self, mandate: Optional[Mandate] = None, paper: bool = True):
        super().__init__(mandate=mandate)
        self.paper_only = paper
        self._api = None
        self._connect()

    def _connect(self):
        try:
            import alpaca_trade_api as tradeapi
            base_url = os.environ.get("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
            self._api = tradeapi.REST(
                os.environ["ALPACA_API_KEY"],
                os.environ["ALPACA_SECRET_KEY"],
                base_url,
            )
        except ImportError:
            logger.warning("alpaca-trade-api not installed. pip install alpaca-trade-api")
        except KeyError as e:
            logger.warning("Missing Alpaca env var: %s", e)

    def _execute_order(self, order: Order) -> Dict:
        if not self._api:
            return {"status": "error", "reason": "Alpaca API not connected"}
        result = self._api.submit_order(
            symbol=order.symbol,
            qty=order.qty,
            side=order.side,
            type=order.order_type,
            time_in_force="gtc",
            limit_price=order.price,
        )
        return {"status": "placed", "order_id": str(result.id)}

    def get_positions(self) -> List[Position]:
        if not self._api:
            return []
        return [
            Position(symbol=p.symbol, qty=float(p.qty), avg_price=float(p.avg_entry_price),
                     current_price=float(p.current_price or 0),
                     pnl=float(p.unrealized_pl or 0),
                     pnl_pct=float(p.unrealized_plpc or 0))
            for p in self._api.list_positions()
        ]

    def get_account(self) -> Dict:
        if not self._api:
            return {}
        acc = self._api.get_account()
        return {"broker": "Alpaca", "equity": float(acc.equity), "cash": float(acc.cash)}

    def _get_price(self, symbol: str) -> float:
        if not self._api:
            return 0.0
        bar = self._api.get_latest_bar(symbol)
        return float(bar.c) if bar else 0.0
