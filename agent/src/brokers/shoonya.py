"""
Shoonya (Finvasia) Broker Connector — SenAlgo by Amit Kumar Sen
Indian NSE/BSE equities and F&O via NorenApi.
pip install NorenRestApiPy
"""
from __future__ import annotations
import hashlib
import os
from typing import Optional
from .base import BrokerBase, Order, Position


class ShoonyaBroker(BrokerBase):
    """Connector for Shoonya / Finvasia."""

    name = "shoonya"

    def __init__(self, user: str = "", pwd: str = "", totp: str = "",
                 vendor_code: str = "", api_secret: str = "",
                 imei: str = "SENALGO", **kwargs):
        super().__init__(**kwargs)
        self.user = user or os.environ.get("SHOONYA_USER", "")
        self.pwd = pwd or os.environ.get("SHOONYA_PASSWORD", "")
        self.totp = totp or os.environ.get("SHOONYA_TOTP", "")
        self.vendor_code = vendor_code or os.environ.get("SHOONYA_VENDOR_CODE", "")
        self.api_secret = api_secret or os.environ.get("SHOONYA_API_SECRET", "")
        self.imei = imei
        self._api = None

    def _get_api(self):
        if self._api is None:
            from NorenRestApiPy.NorenApi import NorenApi
            import pyotp
            self._api = NorenApi(
                host="https://api.shoonya.com/NorenWClient10/",
                websocket="wss://api.shoonya.com/NorenWSTP/",
            )
            sha256_pwd = hashlib.sha256(self.pwd.encode()).hexdigest()
            totp_code = pyotp.TOTP(self.totp).now() if self.totp else ""
            self._api.login(
                userid=self.user,
                password=sha256_pwd,
                twoFA=totp_code,
                vendor_code=self.vendor_code,
                api_secret=self.api_secret,
                imei=self.imei,
            )
        return self._api

    def get_positions(self) -> list[Position]:
        api = self._get_api()
        raw = api.get_positions() or []
        positions = []
        for p in raw:
            qty = int(p.get("netqty", 0))
            if qty != 0:
                positions.append(Position(
                    symbol=p["tsym"],
                    quantity=qty,
                    avg_price=float(p.get("netavgprc", 0)),
                    current_price=float(p.get("lp", 0)),
                    pnl=float(p.get("rpnl", 0)) + float(p.get("urmtom", 0)),
                ))
        return positions

    def place_order(self, order: Order) -> str:
        self._safety_check(order)
        if self.mandate.paper_only:
            return f"[PAPER] Shoonya order: {order.side} {order.quantity} {order.symbol} @ {order.price or 'MKT'}"
        api = self._get_api()
        resp = api.place_order(
            buy_or_sell="B" if order.side == "buy" else "S",
            product_type="I",  # intraday
            exchange="NSE",
            tradingsymbol=order.symbol,
            quantity=order.quantity,
            discloseqty=0,
            price_type="MKT" if order.price is None else "LMT",
            price=order.price or 0,
            trigger_price=None,
            retention="DAY",
            remarks="SenAlgo",
        )
        return resp.get("norenordno", "")

    def cancel_order(self, order_id: str) -> bool:
        api = self._get_api()
        resp = api.cancel_order(orderno=order_id)
        return resp.get("stat") == "Ok"

    def get_quote(self, symbol: str) -> dict:
        api = self._get_api()
        resp = api.get_quotes(exchange="NSE", token=symbol) or {}
        return {"symbol": symbol, "last": float(resp.get("lp", 0))}
