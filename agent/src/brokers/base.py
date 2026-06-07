"""
SenAlgo Broker Base + Safety Layer
by Amit Kumar Sen
"""
from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

AUDIT_PATH = Path.home() / ".senalgo" / "audit_ledger.jsonl"
AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Order:
    symbol: str
    side: str          # "buy" | "sell"
    qty: float
    order_type: str    # "market" | "limit"
    price: Optional[float] = None
    order_id: Optional[str] = None
    status: str = "pending"


@dataclass
class Position:
    symbol: str
    qty: float
    avg_price: float
    current_price: float
    pnl: float
    pnl_pct: float


@dataclass
class Mandate:
    """User-committed trading mandate — safety guardrails."""
    symbols: List[str]                # allowed symbols
    max_order_value: float            # max value per single order
    max_exposure: float               # max total exposure
    daily_loss_cap: float             # max loss per day
    leverage: float = 1.0
    expires: Optional[date] = None

    def allows(self, symbol: str, value: float) -> tuple[bool, str]:
        if symbol not in self.symbols:
            return False, f"Symbol {symbol} not in mandate universe: {self.symbols}"
        if value > self.max_order_value:
            return False, f"Order value {value} exceeds mandate limit {self.max_order_value}"
        if self.expires and date.today() > self.expires:
            return False, f"Mandate expired on {self.expires}"
        return True, "OK"


class BrokerBase(ABC):
    """Abstract broker interface with safety layer."""

    name: str = "BaseBroker"
    paper_only: bool = True

    def __init__(self, mandate: Optional[Mandate] = None, kill_switch_path: Optional[Path] = None):
        self.mandate = mandate
        self.kill_switch_path = kill_switch_path or (Path.home() / ".senalgo" / "KILL_SWITCH")
        self._daily_pnl: float = 0.0

    def place_order(self, order: Order) -> Dict:
        """Place order with full safety checks."""
        # 1. Kill switch
        if self.kill_switch_path.exists():
            logger.error("KILL SWITCH ACTIVE — refusing all orders")
            return {"status": "rejected", "reason": "kill switch active"}

        # 2. Paper-only guard
        if self.paper_only:
            logger.info("[PAPER] Would place: %s %s %s @ %s", order.side, order.qty, order.symbol, order.price)
            return self._paper_fill(order)

        # 3. Mandate check
        if self.mandate:
            price = order.price or self._get_price(order.symbol)
            value = (price or 0) * order.qty
            ok, reason = self.mandate.allows(order.symbol, value)
            if not ok:
                return {"status": "rejected", "reason": reason}

        # 4. Daily loss cap
        if self.mandate and self._daily_pnl < -self.mandate.daily_loss_cap:
            return {"status": "rejected", "reason": f"Daily loss cap hit: {self._daily_pnl:.2f}"}

        # 5. Execute
        result = self._execute_order(order)
        self._audit(order, result)
        return result

    def _paper_fill(self, order: Order) -> Dict:
        fill_price = order.price or 0.0
        result = {
            "status": "filled",
            "paper": True,
            "order_id": f"PAPER-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "symbol": order.symbol,
            "side": order.side,
            "qty": order.qty,
            "fill_price": fill_price,
        }
        self._audit(order, result)
        return result

    def _audit(self, order: Order, result: Dict) -> None:
        entry = {
            "ts": datetime.now().isoformat(),
            "broker": self.name,
            "paper": self.paper_only,
            "order": {"symbol": order.symbol, "side": order.side, "qty": order.qty},
            "result": result,
        }
        with open(AUDIT_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

    @abstractmethod
    def _execute_order(self, order: Order) -> Dict:
        """Broker-specific order execution."""

    @abstractmethod
    def get_positions(self) -> List[Position]:
        """Return current positions."""

    @abstractmethod
    def get_account(self) -> Dict:
        """Return account balance/margin info."""

    @abstractmethod
    def _get_price(self, symbol: str) -> float:
        """Get current price for a symbol."""
