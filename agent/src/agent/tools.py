"""
SenAlgo Agent Tools
by Amit Kumar Sen

Tools available to the AI agent:
  - fetch_ohlcv: Load market data
  - run_smc_analysis: Smart Money Concepts analysis
  - run_volume_analysis: Volume profile + VWAP
  - run_order_flow: Order flow analysis
  - run_backtest: Backtest a strategy
  - run_walk_forward: Walk-forward validation
  - run_monte_carlo: Monte Carlo simulation
  - place_order: Execute a trade (paper/live)
  - get_positions: Current broker positions
  - search_web: DuckDuckGo search
  - create_hypothesis: Add a strategy hypothesis
  - list_hypotheses: View hypothesis registry
"""
from __future__ import annotations
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}
    is_readonly: bool = True

    @abstractmethod
    def execute(self, **kwargs: Any) -> str:
        pass

    def to_openai_schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters or {"type": "object", "properties": {}, "required": []},
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def get_definitions(self) -> List[Dict[str, Any]]:
        return [t.to_openai_schema() for t in self._tools.values()]

    def execute(self, name: str, params: Dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return json.dumps({"status": "error", "error": f"Tool '{name}' not found"})
        try:
            return tool.execute(**params)
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            return json.dumps({"status": "error", "tool": name, "error": str(exc)})

    @property
    def tool_names(self) -> List[str]:
        return list(self._tools.keys())


# ── Concrete Tools ────────────────────────────────────────────────────────────

class FetchOHLCVTool(BaseTool):
    name = "fetch_ohlcv"
    description = "Fetch OHLCV price data for any symbol (NSE, BSE, crypto, forex, US equities)"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Ticker symbol e.g. RELIANCE.NS, BTC-USDT, AAPL"},
            "interval": {"type": "string", "description": "Timeframe: 1m, 5m, 15m, 1h, 4h, 1d, 1wk", "default": "1d"},
            "period": {"type": "string", "description": "Period: 1mo, 3mo, 6mo, 1y, 2y, max", "default": "1y"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1d", period: str = "1y", **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"status": "error", "message": f"No data for {symbol}"})
        return json.dumps({
            "status": "ok",
            "symbol": symbol,
            "rows": len(df),
            "start": str(df.index[0]),
            "end": str(df.index[-1]),
            "latest_close": float(df["close"].iloc[-1]),
            "preview": df.tail(5).to_dict(orient="records"),
        }, default=str)


class SMCAnalysisTool(BaseTool):
    name = "run_smc_analysis"
    description = "Run Smart Money Concepts analysis: Order Blocks, BOS/CHOCH, FVG, Liquidity, Premium/Discount zones"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "interval": {"type": "string", "default": "1d"},
            "period": {"type": "string", "default": "1y"},
            "swing_length": {"type": "integer", "default": 5},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1d", period: str = "1y", swing_length: int = 5, **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.smc.engine import SMCEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"status": "error", "message": "No data"})
        engine = SMCEngine(swing_length=swing_length)
        result = engine.analyze(df)
        return json.dumps({"status": "ok", "symbol": symbol, **result.to_dict()}, default=str)


class VolumeAnalysisTool(BaseTool):
    name = "run_volume_analysis"
    description = "Compute Volume Profile (POC/VAH/VAL), VWAP bands, and cumulative delta"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "interval": {"type": "string", "default": "1d"},
            "period": {"type": "string", "default": "6mo"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1d", period: str = "6mo", **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.volume_profile.engine import VolumeProfileEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"status": "error", "message": "No data"})
        engine = VolumeProfileEngine()
        result = engine.analyze(df)
        return json.dumps({"status": "ok", "symbol": symbol, **result.to_dict()}, default=str)


class OrderFlowTool(BaseTool):
    name = "run_order_flow"
    description = "Analyze order flow: delta, cumulative delta, absorption, imbalances"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "interval": {"type": "string", "default": "1h"},
            "period": {"type": "string", "default": "1mo"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1h", period: str = "1mo", **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.order_flow.engine import OrderFlowEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"status": "error", "message": "No data"})
        engine = OrderFlowEngine()
        result = engine.analyze(df)
        return json.dumps({"status": "ok", "symbol": symbol, **result.to_dict()}, default=str)


class BacktestTool(BaseTool):
    name = "run_backtest"
    description = (
        "Backtest a strategy on historical data. Available engines: "
        "smc, vwap_revert, orb, ema_cross. Returns Sharpe, Sortino, MaxDD, Win Rate, etc."
    )
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "engine": {"type": "string", "enum": ["smc", "vwap_revert", "orb", "ema_cross"], "default": "smc"},
            "interval": {"type": "string", "default": "1d"},
            "period": {"type": "string", "default": "2y"},
            "initial_capital": {"type": "number", "default": 100000},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, engine: str = "smc", interval: str = "1d",
                period: str = "2y", initial_capital: float = 100_000, **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.backtest.engine import BacktestEngine
        from src.backtest.signals import BUILT_IN_ENGINES
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"status": "error", "message": "No data"})
        eng_class = BUILT_IN_ENGINES.get(engine)
        if not eng_class:
            return json.dumps({"status": "error", "message": f"Unknown engine: {engine}"})
        runner = BacktestEngine(initial_capital=initial_capital)
        result = runner.run(df, eng_class(), symbol=symbol)
        return json.dumps({"status": "ok", **result.to_dict()}, default=str)


class WalkForwardTool(BaseTool):
    name = "run_walk_forward"
    description = "Run walk-forward validation to check strategy robustness"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "engine": {"type": "string", "default": "smc"},
            "period": {"type": "string", "default": "3y"},
            "n_splits": {"type": "integer", "default": 5},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, engine: str = "smc", period: str = "3y", n_splits: int = 5, **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.backtest.engine import BacktestEngine
        from src.backtest.signals import BUILT_IN_ENGINES
        df = load_ohlcv(symbol, interval="1d", period=period)
        if df.empty:
            return json.dumps({"status": "error"})
        eng_class = BUILT_IN_ENGINES.get(engine, BUILT_IN_ENGINES["ema_cross"])
        runner = BacktestEngine()
        results = runner.walk_forward(df, eng_class(), n_splits=n_splits, symbol=symbol)
        return json.dumps({
            "status": "ok",
            "splits": [r.to_dict() for r in results],
            "avg_sharpe": sum(r.metrics.sharpe for r in results) / len(results) if results else 0,
        }, default=str)


class MonteCarloTool(BaseTool):
    name = "run_monte_carlo"
    description = "Monte Carlo simulation of strategy returns to assess robustness"
    parameters = {
        "type": "object",
        "properties": {
            "symbol": {"type": "string"},
            "engine": {"type": "string", "default": "smc"},
            "n_simulations": {"type": "integer", "default": 1000},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, engine: str = "smc", n_simulations: int = 1000, **kwargs) -> str:
        from src.market_data.loader import load_ohlcv
        from src.backtest.engine import BacktestEngine
        from src.backtest.signals import BUILT_IN_ENGINES
        df = load_ohlcv(symbol, interval="1d", period="2y")
        if df.empty:
            return json.dumps({"status": "error"})
        eng_class = BUILT_IN_ENGINES.get(engine, BUILT_IN_ENGINES["ema_cross"])
        runner = BacktestEngine()
        result = runner.run(df, eng_class(), symbol=symbol)
        mc = runner.monte_carlo(result.trades, n_simulations=n_simulations)
        return json.dumps({"status": "ok", **mc}, default=str)


class WebSearchTool(BaseTool):
    name = "search_web"
    description = "Search the web for market news, financial data, or trading research"
    parameters = {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    }

    def execute(self, query: str, max_results: int = 5, **kwargs) -> str:
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            return json.dumps({"status": "ok", "results": results})
        except Exception as e:
            return json.dumps({"status": "error", "error": str(e)})


class CreateHypothesisTool(BaseTool):
    name = "create_hypothesis"
    description = "Create a strategy hypothesis for testing in the self-improvement loop"
    is_readonly = False
    parameters = {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "What the hypothesis proposes"},
            "strategy_code": {"type": "string", "description": "Python code for the strategy (optional)"},
        },
        "required": ["description"],
    }

    def execute(self, description: str, strategy_code: str = "", **kwargs) -> str:
        from src.self_improve.loop import HypothesisRegistry
        registry = HypothesisRegistry()
        h = registry.create(description=description, strategy_code=strategy_code)
        return json.dumps({"status": "ok", "hypothesis_id": h.id, "description": h.description})


class ListHypothesesTool(BaseTool):
    name = "list_hypotheses"
    description = "List all strategy hypotheses in the registry"
    parameters = {
        "type": "object",
        "properties": {
            "status": {"type": "string", "description": "Filter by status: pending|testing|validated|rejected"},
        },
    }

    def execute(self, status: Optional[str] = None, **kwargs) -> str:
        from src.self_improve.loop import HypothesisRegistry
        registry = HypothesisRegistry()
        hypotheses = registry.list_all(status=status)
        return json.dumps({
            "status": "ok",
            "count": len(hypotheses),
            "hypotheses": [h.to_dict() for h in hypotheses],
        })


def build_tool_registry() -> ToolRegistry:
    """Build and return the default SenAlgo tool registry."""
    registry = ToolRegistry()
    for tool_cls in [
        FetchOHLCVTool,
        SMCAnalysisTool,
        VolumeAnalysisTool,
        OrderFlowTool,
        BacktestTool,
        WalkForwardTool,
        MonteCarloTool,
        WebSearchTool,
        CreateHypothesisTool,
        ListHypothesesTool,
    ]:
        registry.register(tool_cls())
    return registry


# ---------------------------------------------------------------------------
# New tools for expanded feature set
# ---------------------------------------------------------------------------

class ElliottWaveTool(BaseTool):
    name = "elliott_wave_analysis"
    description = "Analyze Elliott Wave patterns (impulse 5-wave and corrective ABC) with Fibonacci projections"
    parameters = {
        "type": "object",
        "properties": {
            "symbol":   {"type": "string", "description": "Ticker symbol"},
            "interval": {"type": "string", "default": "1d"},
            "period":   {"type": "string", "default": "2y"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1d", period: str = "2y") -> str:
        from market_data.loader import load_ohlcv
        from strategies.elliott_wave import ElliottWaveAnalyzer
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"error": f"No data for {symbol}"})
        result = ElliottWaveAnalyzer().analyze(df)
        return json.dumps(result.to_dict(), indent=2)


class ICTAnalysisTool(BaseTool):
    name = "ict_analysis"
    description = "Analyze ICT concepts: Power of 3 (AMD), Kill Zones, OTE, Breaker Blocks, NDOG"
    parameters = {
        "type": "object",
        "properties": {
            "symbol":   {"type": "string"},
            "interval": {"type": "string", "default": "1h"},
            "period":   {"type": "string", "default": "30d"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1h", period: str = "30d") -> str:
        from market_data.loader import load_ohlcv
        from strategies.ict_concepts import ICTEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"error": f"No data for {symbol}"})
        result = ICTEngine().analyze(df)
        return json.dumps(result.to_dict(), indent=2)


class CRTAnalysisTool(BaseTool):
    name = "crt_analysis"
    description = "Candle Range Theory analysis — detect manipulation raids and fill setups across HTF candles"
    parameters = {
        "type": "object",
        "properties": {
            "symbol":     {"type": "string"},
            "interval":   {"type": "string", "default": "5m"},
            "period":     {"type": "string", "default": "7d"},
            "htf_period": {"type": "integer", "default": 4},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "5m",
                period: str = "7d", htf_period: int = 4) -> str:
        from market_data.loader import load_ohlcv
        from strategies.candle_range_theory import CRTEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"error": f"No data for {symbol}"})
        result = CRTEngine(htf_period=htf_period).analyze(df)
        return json.dumps(result.to_dict(), indent=2)


class MultiFactorTool(BaseTool):
    name = "multi_factor_analysis"
    description = "Compute 452+ pre-built quant alpha factors (Alpha101, GTJA191, Qlib158, FF5+Carhart) and get composite signal"
    parameters = {
        "type": "object",
        "properties": {
            "symbol":   {"type": "string"},
            "interval": {"type": "string", "default": "1d"},
            "period":   {"type": "string", "default": "5y"},
            "factors":  {"type": "array", "items": {"type": "string"}, "description": "Specific factors to run (empty = all)"},
        },
        "required": ["symbol"],
    }

    def execute(self, symbol: str, interval: str = "1d",
                period: str = "5y", factors: list = None) -> str:
        from market_data.loader import load_ohlcv
        from strategies.multi_factor import MultiFactorEngine
        df = load_ohlcv(symbol, interval=interval, period=period)
        if df.empty:
            return json.dumps({"error": f"No data for {symbol}"})
        result = MultiFactorEngine(factors or None).analyze(df)
        return json.dumps(result.to_dict(), indent=2)


class GeneratePineScriptTool(BaseTool):
    name = "generate_pine_script"
    description = "Generate TradingView Pine Script v6 code for indicators or strategies (SMC, ICT, Elliott Wave, VWAP, ORB, CRT, custom)"
    parameters = {
        "type": "object",
        "properties": {
            "template": {
                "type": "string",
                "description": "Template name: smc_order_blocks | ict_kill_zones | elliott_wave | volume_profile_vwap | orb_strategy | crt_indicator | custom",
            },
            "custom_name":      {"type": "string", "description": "Name for custom script"},
            "script_type":      {"type": "string", "description": "indicator or strategy"},
            "indicators":       {"type": "array", "items": {"type": "string"}},
            "entry_rules":      {"type": "string"},
            "exit_rules":       {"type": "string"},
        },
        "required": ["template"],
    }

    def execute(self, template: str, custom_name: str = "Custom Strategy",
                script_type: str = "strategy", indicators: list = None,
                entry_rules: str = "", exit_rules: str = "") -> str:
        from pinescript.generator import PineScriptGenerator
        gen = PineScriptGenerator()
        if template == "custom":
            result = gen.generate_custom(
                name=custom_name,
                script_type=script_type,
                indicators=indicators or [],
                entry_rules=entry_rules,
                exit_rules=exit_rules,
            )
        else:
            result = gen.generate(template)
        return json.dumps({
            "name": result.name,
            "version": f"Pine Script v{result.version}",
            "file_name": result.file_name,
            "code": result.code,
            "available_templates": gen.list_templates(),
        }, indent=2)


class ShadowAccountTool(BaseTool):
    name = "analyze_shadow_account"
    description = "Analyze your broker trade journal CSV export — win rate, profit factor, best/worst patterns, improvement hypotheses"
    parameters = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string", "description": "Path to broker trade journal CSV"},
            "broker":    {"type": "string", "description": "Broker name: zerodha|fyers|dhan|alpaca|ibkr|generic"},
        },
        "required": ["file_path"],
    }

    def execute(self, file_path: str, broker: str = "generic") -> str:
        from shadow_account.analyzer import ShadowAccountAnalyzer
        analyzer = ShadowAccountAnalyzer(broker=broker)
        result = analyzer.analyze_file(file_path)
        return json.dumps(result.to_dict(), indent=2)


class SwarmAnalysisTool(BaseTool):
    name = "swarm_analysis"
    description = "Run multi-agent swarm analysis — multiple AI specialist agents debate and reach consensus on a trading question"
    parameters = {
        "type": "object",
        "properties": {
            "topic":   {"type": "string", "description": "Question or asset to analyze"},
            "preset":  {"type": "string", "description": "Swarm preset: investment_committee|quant_desk|crypto_desk|smc_team|india_fno_desk|full_committee"},
            "context": {"type": "string", "description": "Optional market context / prior analysis to include"},
        },
        "required": ["topic"],
    }

    def execute(self, topic: str, preset: str = "investment_committee",
                context: str = "") -> str:
        import os
        from swarm.agents import SwarmOrchestrator
        provider = os.environ.get("SENALGO_LLM_PROVIDER", "ollama")
        orch = SwarmOrchestrator(llm_provider=provider)
        result = orch.run(topic=topic, preset=preset, context=context)
        return json.dumps(result.to_dict(), indent=2)


class ListBrokersConnectorsTool(BaseTool):
    name = "list_broker_connectors"
    description = "List all supported broker connectors in SenAlgo"
    parameters = {"type": "object", "properties": {}}

    def execute(self) -> str:
        brokers = {
            "Indian": ["Zerodha Kite", "Fyers (+ live data feed)", "Dhan", "Shoonya/Finvasia"],
            "US": ["Alpaca", "Robinhood (paper)", "Interactive Brokers (IBKR)"],
            "Global": ["Tiger Brokers", "Futu/Moomoo", "Longbridge"],
            "Crypto": ["Binance", "OKX", "CCXT (100+ exchanges via ccxt library)"],
        }
        return json.dumps(brokers, indent=2)


def build_tool_registry():
    """Build the complete SenAlgo tool registry."""
    from agent.tools import ToolRegistry  # avoid circular if needed
    registry = ToolRegistry()
    # Core tools
    for ToolClass in [
        FetchOHLCVTool, SMCAnalysisTool, VolumeAnalysisTool, OrderFlowTool,
        BacktestTool, WalkForwardTool, MonteCarloTool, WebSearchTool,
        CreateHypothesisTool, ListHypothesesTool,
        # New expanded tools
        ElliottWaveTool, ICTAnalysisTool, CRTAnalysisTool,
        MultiFactorTool, GeneratePineScriptTool, ShadowAccountTool,
        SwarmAnalysisTool, ListBrokersConnectorsTool,
    ]:
        try:
            registry.register(ToolClass())
        except Exception:
            pass
    return registry
