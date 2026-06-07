"""
SenAlgo AI Agent Loop (ReAct pattern)
by Amit Kumar Sen

Supports 12+ LLM providers — Ollama (local, free) is the default.
No API key required to get started.

Supported providers:
  ollama      — local, completely free (default)
  deepseek    — ultra-cheap API
  groq        — free tier, fast
  openrouter  — 200+ models
  gemini      — Google Gemini
  openai      — GPT-4o / o1
  anthropic   — Claude
  dashscope   — Alibaba Qwen
  zhipu       — GLM-4
  moonshot    — Kimi
  minimax     — MiniMax
  zai         — Z.ai
"""
from __future__ import annotations
import json
import logging
import os
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "ollama":     "qwen2.5:14b",
    "deepseek":   "deepseek-chat",
    "groq":       "llama-3.3-70b-versatile",
    "openrouter": "deepseek/deepseek-chat",
    "gemini":     "gemini-2.0-flash",
    "openai":     "gpt-4o",
    "anthropic":  "claude-sonnet-4-6",
    "dashscope":  "qwen-max",
    "zhipu":      "glm-4",
    "moonshot":   "moonshot-v1-8k",
    "minimax":    "abab6.5-chat",
    "zai":        "z1-mini",
}

PROVIDER_BASE_URLS = {
    "ollama":     "http://localhost:11434/v1",
    "deepseek":   "https://api.deepseek.com/v1",
    "groq":       "https://api.groq.com/openai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "gemini":     "https://generativelanguage.googleapis.com/v1beta/openai",
    "dashscope":  "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "zhipu":      "https://open.bigmodel.cn/api/paas/v4",
    "moonshot":   "https://api.moonshot.cn/v1",
    "minimax":    "https://api.minimax.chat/v1",
    "zai":        "https://api.z.ai/v1",
}

SYSTEM_PROMPT = """You are SenAlgo — an expert AI trading agent created by Amit Kumar Sen.

STRATEGIES & ANALYSIS YOU MASTER
- Smart Money Concepts (SMC): Order Blocks, BOS/CHOCH, FVG, Liquidity sweeps, Premium/Discount
- ICT Concepts: Power of 3, Kill Zones, OTE, Breaker Blocks, Mitigation Blocks, NWOG/NDOG
- Elliott Wave Theory: 5-wave impulse, ABC corrective, WXY complex, Fibonacci ratios
- Candle Range Theory (CRT): Forming candle, Raid, Fill — intra-candle manipulation
- Opening Range Breakout (ORB): First 15/30/60-min range, breakout confirmation
- Price Action: S/R, Pin Bars, Engulfing, Inside Bars, Doji, Morning/Evening Star
- Auction Market Theory: Value Area, POC, TPO/Market Profile distributions
- Momentum: RSI divergence, MACD histogram, Stochastic, Williams %R
- Mean Reversion: Bollinger Bands, VWAP deviation, Z-score
- Multi-factor Quant: Alpha101, GTJA191, Qlib158, FF5+Carhart
- HFT Order Flow: Footprint, Cumulative Delta, Absorption, Imbalances
- Volume Profile: POC/VAH/VAL, VWAP + 3 std dev bands
- 452 pre-built Alpha Zoo factors

MARKETS
- India: NSE/BSE equities & F&O (real-time via Fyers WebSocket)
- US: NYSE/NASDAQ; HK equities; Forex; Commodities; Indices
- Crypto: 100+ exchanges via CCXT (OKX, Binance, Bybit …)

PINE SCRIPT v6
When asked to generate Pine Script, ALWAYS target version 6:
  - Start with: //@version=6
  - Use proper type annotations (float, int, bool, series float …)
  - Use var for persistent variables
  - Use array.new<float>() syntax (not array.new_float())
  - Prefer switch/if expressions over ternary chains
  - Include proper strategy() or indicator() declaration
  - Add alert conditions with alertcondition()

BROKERS (paper-safe by default)
Indian: Zerodha Kite, Fyers, Dhan, Shoonya
US / Global: Alpaca, Robinhood, IBKR, Tiger, Futu, Longbridge
Crypto: Binance, OKX, CCXT (100+ exchanges)

Always cite analysis with price levels, percentages, and confidence.
Use markdown tables for comparisons. Never fabricate — use tools for real data.
"""

MAX_ITERATIONS = 50


class AgentLoop:
    """ReAct agent loop — supports 12+ LLM providers via OpenAI-compat API."""

    def __init__(
        self,
        tool_registry,
        llm_provider: str = "ollama",
        model: str = "",
        api_key: str = "",
        api_base: str = "",
        max_iterations: int = MAX_ITERATIONS,
        on_progress: Optional[Callable[[str], None]] = None,
    ):
        self.tools = tool_registry
        self.llm_provider = llm_provider
        self.model = model or DEFAULT_MODELS.get(llm_provider, "")
        self.api_key = api_key
        self.api_base = api_base or PROVIDER_BASE_URLS.get(llm_provider, "")
        self.max_iterations = max_iterations
        self.on_progress = on_progress or (lambda x: None)
        self._messages: List[Dict] = []
        self._cancelled = False

    # ------------------------------------------------------------------
    def chat(self, user_message: str) -> Generator[str, None, None]:
        self._messages.append({"role": "user", "content": user_message})
        yield from self._run_loop()

    def run(self, user_message: str) -> str:
        result = ""
        for chunk in self.chat(user_message):
            result = chunk
        return result

    def cancel(self) -> None:
        self._cancelled = True

    def reset(self) -> None:
        self._messages = []
        self._cancelled = False

    # ------------------------------------------------------------------
    def _run_loop(self) -> Generator[str, None, None]:
        self._cancelled = False
        iteration = 0
        while iteration < self.max_iterations and not self._cancelled:
            iteration += 1
            self.on_progress(f"[Iteration {iteration}] Thinking…")
            response = self._call_llm()
            if not response:
                break

            stop = response.get("stop_reason", "")
            tool_calls = self._extract_tool_calls(response)

            if not tool_calls or stop in ("end_turn", "stop"):
                text = self._extract_text(response)
                if text:
                    self._messages.append({"role": "assistant", "content": text})
                    yield text
                break

            text = self._extract_text(response)
            self._messages.append(
                {"role": "assistant", "content": text, "tool_calls": tool_calls}
            )
            tool_results = self._execute_tools(tool_calls)
            self._messages.append({"role": "tool", "content": json.dumps(tool_results)})
            yield f"[Tools: {', '.join(tc['name'] for tc in tool_calls)}]"

        if iteration >= self.max_iterations:
            yield "Reached maximum iterations. Please narrow your request."

    # ------------------------------------------------------------------
    def _call_llm(self) -> Optional[Dict]:
        try:
            if self.llm_provider == "anthropic":
                return self._call_anthropic()
            return self._call_openai_compat()
        except Exception as exc:
            logger.error("LLM call failed (%s): %s", self.llm_provider, exc)
            return None

    def _call_anthropic(self) -> Dict:
        import anthropic
        key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        client = anthropic.Anthropic(api_key=key)
        tools = self.tools.get_definitions()
        at = [
            {"name": t["function"]["name"],
             "description": t["function"]["description"],
             "input_schema": t["function"].get("parameters", {})}
            for t in tools
        ]
        resp = client.messages.create(
            model=self.model or "claude-sonnet-4-6",
            max_tokens=8096,
            system=SYSTEM_PROMPT,
            messages=self._messages,
            tools=at,
        )
        return {"stop_reason": resp.stop_reason, "content": resp.content}

    def _call_openai_compat(self) -> Dict:
        """Works for Ollama, DeepSeek, Groq, Gemini, OpenRouter, Zhipu,
        Moonshot, DashScope, MiniMax, Z.ai, OpenAI itself."""
        from openai import OpenAI
        client = OpenAI(
            api_key=self.api_key or "ollama",
            base_url=self.api_base or None,
        )
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + self._messages
        tools = self.tools.get_definitions()
        kwargs: Dict[str, Any] = dict(
            model=self.model,
            messages=messages,
            temperature=0.0,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        resp = client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        return {"stop_reason": choice.finish_reason, "content": choice.message}

    # ------------------------------------------------------------------
    def _extract_text(self, response: Dict) -> str:
        content = response.get("content", "")
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join(b.text for b in content if hasattr(b, "text") and b.text)
        if hasattr(content, "content"):
            return content.content or ""
        return str(content)

    def _extract_tool_calls(self, response: Dict) -> List[Dict]:
        content = response.get("content", [])
        calls: List[Dict] = []
        if isinstance(content, list):
            for block in content:
                if getattr(block, "type", None) == "tool_use":
                    calls.append({"name": block.name, "id": block.id, "input": block.input})
        elif hasattr(content, "tool_calls") and content.tool_calls:
            for tc in content.tool_calls:
                calls.append({
                    "name": tc.function.name,
                    "id": tc.id,
                    "input": json.loads(tc.function.arguments or "{}"),
                })
        return calls

    def _execute_tools(self, tool_calls: List[Dict]) -> List[Dict]:
        results = []
        for tc in tool_calls:
            self.on_progress(f"Running tool: {tc['name']}…")
            result_str = self.tools.execute(tc["name"], tc.get("input", {}))
            results.append({"tool_call_id": tc.get("id"), "name": tc["name"], "result": result_str})
        return results
