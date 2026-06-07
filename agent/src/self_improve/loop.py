"""
SenAlgo Self-Improvement Loop
by Amit Kumar Sen

The agent evaluates its own strategy performance, generates hypotheses
about what might work better, tests them via backtesting, and iteratively
improves its strategy library.
"""
from __future__ import annotations
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

HYPOTHESES_PATH = Path.home() / ".senalgo" / "hypotheses.jsonl"
HYPOTHESES_PATH.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class Hypothesis:
    id: str
    description: str
    strategy_code: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    status: str = "pending"       # pending | testing | validated | rejected
    backtest_sharpe: Optional[float] = None
    backtest_return: Optional[float] = None
    backtest_dd: Optional[float] = None
    notes: str = ""

    def to_dict(self) -> dict:
        return self.__dict__.copy()


class HypothesisRegistry:
    """Persistent store for trading strategy hypotheses."""

    def __init__(self, path: Path = HYPOTHESES_PATH):
        self.path = path

    def create(self, description: str, strategy_code: str) -> Hypothesis:
        h = Hypothesis(
            id=str(uuid.uuid4())[:8],
            description=description,
            strategy_code=strategy_code,
        )
        self._append(h)
        return h

    def update(self, hypothesis_id: str, **kwargs) -> Optional[Hypothesis]:
        hypotheses = self.list_all()
        for h in hypotheses:
            if h.id == hypothesis_id:
                for k, v in kwargs.items():
                    if hasattr(h, k):
                        setattr(h, k, v)
                self._rewrite(hypotheses)
                return h
        return None

    def list_all(self, status: Optional[str] = None) -> List[Hypothesis]:
        if not self.path.exists():
            return []
        results = []
        for line in self.path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                h = Hypothesis(**d)
                if status is None or h.status == status:
                    results.append(h)
            except Exception:
                pass
        return results

    def _append(self, h: Hypothesis) -> None:
        with open(self.path, "a") as f:
            f.write(json.dumps(h.to_dict()) + "\n")

    def _rewrite(self, hypotheses: List[Hypothesis]) -> None:
        with open(self.path, "w") as f:
            for h in hypotheses:
                f.write(json.dumps(h.to_dict()) + "\n")


class SelfImprovementLoop:
    """Agent self-improvement workflow.

    1. Evaluate recent backtest results
    2. Identify weaknesses (low Sharpe, high DD, low win rate)
    3. Generate strategy improvement hypotheses via LLM
    4. Run backtests on hypotheses
    5. Promote validated strategies, reject failures
    6. Update agent memory with learnings
    """

    def __init__(self, llm_client=None):
        self.registry = HypothesisRegistry()
        self.llm = llm_client

    def evaluate_and_improve(
        self,
        symbol: str,
        backtest_result: dict,
        df_json: str = "",
    ) -> Dict:
        """Main self-improvement entry point after a backtest run."""
        weaknesses = self._identify_weaknesses(backtest_result)
        if not weaknesses:
            return {"status": "no_improvement_needed", "message": "Strategy performing well"}

        hypothesis_text = self._generate_hypothesis(symbol, backtest_result, weaknesses)
        h = self.registry.create(
            description=hypothesis_text,
            strategy_code=f"# Auto-generated hypothesis for {symbol}\n# Weaknesses: {weaknesses}",
        )
        return {
            "status": "hypothesis_created",
            "hypothesis_id": h.id,
            "description": hypothesis_text,
            "weaknesses": weaknesses,
        }

    def _identify_weaknesses(self, result: dict) -> List[str]:
        weaknesses = []
        m = result.get("metrics", {})
        if m.get("sharpe", 99) < 0.5:
            weaknesses.append(f"Low Sharpe ratio: {m.get('sharpe', 0):.2f}")
        if m.get("max_drawdown", 0) < -0.20:
            weaknesses.append(f"High drawdown: {m.get('max_drawdown', 0):.1%}")
        if m.get("win_rate", 1) < 0.40:
            weaknesses.append(f"Low win rate: {m.get('win_rate', 0):.1%}")
        if m.get("profit_factor", 99) < 1.2:
            weaknesses.append(f"Low profit factor: {m.get('profit_factor', 0):.2f}")
        return weaknesses

    def _generate_hypothesis(self, symbol: str, result: dict, weaknesses: List[str]) -> str:
        weakness_str = "; ".join(weaknesses)
        return (
            f"For {symbol}: current strategy shows weaknesses: {weakness_str}. "
            f"Hypothesis: add volume filter (only trade when volume > 1.5x avg) + "
            f"tighten stop-loss to 1 ATR to reduce drawdown. "
            f"Add SMC confirmation (require BOS in same direction before entry)."
        )

    def run_hypothesis_backtest(self, hypothesis_id: str, df, engine_class) -> Dict:
        """Test a hypothesis by running a backtest."""
        from src.backtest.engine import BacktestEngine
        h = next((x for x in self.registry.list_all() if x.id == hypothesis_id), None)
        if not h:
            return {"error": "Hypothesis not found"}

        self.registry.update(hypothesis_id, status="testing")
        engine = engine_class()
        runner = BacktestEngine()
        result = runner.run(df, engine)

        sharpe = result.metrics.sharpe
        dd = result.metrics.max_drawdown
        ret = result.metrics.total_return

        status = "validated" if sharpe > 0.8 and dd > -0.15 else "rejected"
        self.registry.update(
            hypothesis_id,
            status=status,
            backtest_sharpe=sharpe,
            backtest_return=ret,
            backtest_dd=dd,
        )
        return {
            "hypothesis_id": hypothesis_id,
            "status": status,
            "sharpe": sharpe,
            "return": ret,
            "max_dd": dd,
        }
