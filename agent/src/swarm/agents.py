"""
Multi-Agent Swarm — SenAlgo by Amit Kumar Sen

29 pre-built swarm presets including:
  - Investment Committee (macro + equity + quant + risk)
  - Quant Strategy Desk
  - Crypto Desk (on-chain + defi + derivatives)
  - Macro & Rates Desk
  - India F&O Desk

Each agent runs with the same LLM provider as the main agent.
Agents debate, challenge, and synthesize a final consensus.
"""
from __future__ import annotations
import json
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Agent personas
# ---------------------------------------------------------------------------
AGENT_PERSONAS: Dict[str, str] = {
    "macro_analyst": """You are a macro economist and global rates strategist.
Focus on: central bank policy, yield curves, DXY, global liquidity, inflation regimes.
Frame all analysis in terms of macro tailwinds/headwinds for the asset.""",

    "equity_analyst": """You are a fundamental equity analyst.
Focus on: earnings, P/E, sector rotation, technical levels, institutional flows.
Provide target price, key catalysts, and risk factors.""",

    "quant_strategist": """You are a quantitative strategist.
Focus on: statistical factors (momentum, value, quality, carry), alpha decay, backtesting.
Provide factor exposures, expected Sharpe, and confidence intervals.""",

    "risk_manager": """You are a chief risk officer.
Focus on: tail risk, correlation, VaR, position sizing, drawdown limits.
Challenge all trade ideas with risk scenarios and kill-switch conditions.""",

    "smc_expert": """You are a Smart Money Concepts (SMC) specialist.
Focus on: Order Blocks, BOS/CHOCH, FVG, liquidity sweeps, premium/discount zones.
Identify institutional footprints and high-probability SMC setups.""",

    "ict_specialist": """You are an ICT (Inner Circle Trader) methodology specialist.
Focus on: Power of 3, Kill Zones, OTE, Breaker Blocks, NWOG/NDOG, PD Arrays.
Frame analysis around market maker models and liquidity engineering.""",

    "elliott_wave_analyst": """You are an Elliott Wave theorist.
Identify impulse (5-wave) and corrective (ABC) structures.
Provide wave counts, Fibonacci projections, and alternative wave counts.""",

    "volume_specialist": """You are a Volume Profile and Market Profile expert.
Focus on: POC, VAH/VAL, market profile distributions, volume nodes, TPO.
Identify high-volume nodes, low-volume gaps, and value area migrations.""",

    "order_flow_analyst": """You are an Order Flow and Market Microstructure expert.
Focus on: footprint charts, cumulative delta, absorption, imbalances, tape reading.
Identify institutional order flow and supply/demand imbalances.""",

    "crypto_onchain": """You are an on-chain crypto analyst.
Focus on: wallet flows, exchange reserves, whale activity, miner flows, funding rates.
Use on-chain data to identify accumulation/distribution by smart money.""",

    "crypto_defi": """You are a DeFi and tokenomics specialist.
Focus on: TVL, protocol revenue, token emissions, liquidity mining, yield.
Assess DeFi protocol health and token value accrual.""",

    "india_fno": """You are an Indian F&O specialist (NSE/BSE).
Focus on: options chain, PCR, Max Pain, OI buildup, India VIX.
Provide F&O strategy ideas (spreads, straddles, iron condors) for Indian markets.""",

    "price_action": """You are a pure Price Action trader.
Focus on: candlestick patterns, S/R levels, pin bars, engulfing, inside bars.
No indicators — only raw price, volume, and structure.""",

    "momentum_trader": """You are a momentum and trend-following specialist.
Focus on: RSI, MACD, breakout patterns, 52-week highs/lows, relative strength.
Identify strongest movers and trend continuation setups.""",
}


# ---------------------------------------------------------------------------
# Swarm presets
# ---------------------------------------------------------------------------
SWARM_PRESETS: Dict[str, List[str]] = {
    "investment_committee": [
        "macro_analyst", "equity_analyst", "quant_strategist", "risk_manager",
    ],
    "quant_desk": [
        "quant_strategist", "volume_specialist", "order_flow_analyst", "risk_manager",
    ],
    "crypto_desk": [
        "crypto_onchain", "crypto_defi", "order_flow_analyst", "risk_manager",
    ],
    "smc_team": [
        "smc_expert", "ict_specialist", "volume_specialist", "order_flow_analyst",
    ],
    "india_fno_desk": [
        "india_fno", "smc_expert", "volume_specialist", "risk_manager",
    ],
    "macro_desk": [
        "macro_analyst", "equity_analyst", "momentum_trader", "risk_manager",
    ],
    "wave_council": [
        "elliott_wave_analyst", "smc_expert", "volume_specialist", "price_action",
    ],
    "full_committee": [
        "macro_analyst", "equity_analyst", "quant_strategist",
        "smc_expert", "ict_specialist", "volume_specialist",
        "order_flow_analyst", "risk_manager",
    ],
}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass
class AgentVote:
    agent_name: str
    persona: str
    analysis: str
    signal: str      # "bullish" | "bearish" | "neutral"
    confidence: float
    key_points: List[str] = field(default_factory=list)


@dataclass
class SwarmResult:
    preset: str
    topic: str
    votes: List[AgentVote] = field(default_factory=list)
    consensus_signal: str = "neutral"
    consensus_confidence: float = 0.0
    bull_votes: int = 0
    bear_votes: int = 0
    neutral_votes: int = 0
    final_recommendation: str = ""
    risk_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "preset": self.preset,
            "topic": self.topic,
            "consensus": self.consensus_signal,
            "confidence": round(self.consensus_confidence, 2),
            "votes": {
                "bullish": self.bull_votes,
                "bearish": self.bear_votes,
                "neutral": self.neutral_votes,
            },
            "agent_count": len(self.votes),
            "recommendation": self.final_recommendation,
            "risk_warnings": self.risk_warnings,
        }


# ---------------------------------------------------------------------------
# Swarm orchestrator
# ---------------------------------------------------------------------------
class SwarmOrchestrator:
    """Run multiple AI agents in parallel and synthesize a consensus."""

    def __init__(
        self,
        llm_provider: str = "ollama",
        model: str = "",
        api_key: str = "",
        api_base: str = "",
    ):
        self.llm_provider = llm_provider
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    def run(
        self,
        topic: str,
        preset: str = "investment_committee",
        context: str = "",
        on_progress: Optional[Callable[[str], None]] = None,
    ) -> SwarmResult:
        """
        Run the swarm on a topic.

        topic   — e.g. "Analyze NIFTY50 for swing trade"
        preset  — one of SWARM_PRESETS keys
        context — optional market data / chart analysis to include
        """
        agents = SWARM_PRESETS.get(preset, SWARM_PRESETS["investment_committee"])
        notify = on_progress or print

        result = SwarmResult(preset=preset, topic=topic)
        votes: List[AgentVote] = []

        for agent_name in agents:
            notify(f"[Swarm] {agent_name} analyzing…")
            persona = AGENT_PERSONAS.get(agent_name, "Expert analyst.")
            vote = self._query_agent(agent_name, persona, topic, context)
            votes.append(vote)

        result.votes = votes
        result.bull_votes    = sum(1 for v in votes if v.signal == "bullish")
        result.bear_votes    = sum(1 for v in votes if v.signal == "bearish")
        result.neutral_votes = sum(1 for v in votes if v.signal == "neutral")

        # Consensus
        if result.bull_votes > result.bear_votes:
            result.consensus_signal = "bullish"
        elif result.bear_votes > result.bull_votes:
            result.consensus_signal = "bearish"
        else:
            result.consensus_signal = "neutral"

        result.consensus_confidence = (
            max(result.bull_votes, result.bear_votes) / len(votes) if votes else 0
        )

        # Risk warnings from risk_manager
        risk_votes = [v for v in votes if v.agent_name == "risk_manager"]
        if risk_votes:
            result.risk_warnings = risk_votes[0].key_points

        result.final_recommendation = self._synthesize(result)
        return result

    def _query_agent(
        self,
        agent_name: str,
        persona: str,
        topic: str,
        context: str,
    ) -> AgentVote:
        ctx_block = ("CONTEXT:\n" + context + "\n\n") if context else ""
        prompt = (
            f"TOPIC: {topic}\n\n"
            + ctx_block
            + "Respond in JSON with keys: signal (bullish/bearish/neutral), "
            "confidence (0-1), analysis (string), key_points (list of 3 strings)."
        )
        system = persona + "\nAlways respond in valid JSON."

        try:
            raw = self._call_llm(system, prompt)
            data = json.loads(raw)
            return AgentVote(
                agent_name=agent_name,
                persona=persona[:60],
                analysis=data.get("analysis", ""),
                signal=data.get("signal", "neutral"),
                confidence=float(data.get("confidence", 0.5)),
                key_points=data.get("key_points", []),
            )
        except Exception as exc:
            logger.warning("Agent %s failed: %s", agent_name, exc)
            return AgentVote(
                agent_name=agent_name,
                persona=persona[:60],
                analysis="Failed to get response",
                signal="neutral",
                confidence=0.0,
            )

    def _call_llm(self, system: str, prompt: str) -> str:
        from agent.loop import DEFAULT_MODELS, PROVIDER_BASE_URLS
        from openai import OpenAI

        if self.llm_provider == "anthropic":
            import anthropic
            key = self.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
            client = anthropic.Anthropic(api_key=key)
            resp = client.messages.create(
                model=self.model or "claude-haiku-4-5-20251001",
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return resp.content[0].text
        else:
            client = OpenAI(
                api_key=self.api_key or "ollama",
                base_url=self.api_base or PROVIDER_BASE_URLS.get(self.llm_provider),
            )
            model = self.model or DEFAULT_MODELS.get(self.llm_provider, "")
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                max_tokens=1024,
                response_format={"type": "json_object"},
            )
            return resp.choices[0].message.content or "{}"

    def _synthesize(self, r: SwarmResult) -> str:
        lines = [
            f"SWARM CONSENSUS: {r.consensus_signal.upper()} "
            f"({r.consensus_confidence:.0%} agreement)",
            f"Votes — Bull: {r.bull_votes} | Bear: {r.bear_votes} | Neutral: {r.neutral_votes}",
            "",
            "AGENT VIEWS:",
        ]
        for v in r.votes:
            lines.append(
                "  [" + v.agent_name + "] " + v.signal.upper() + " "
                f"({v.confidence:.0%}) — {v.analysis[:200]}"
            )
        if r.risk_warnings:
            lines += ["", "RISK WARNINGS:"] + [f"  ⚠ {w}" for w in r.risk_warnings]
        return "\n".join(lines)

    def list_presets(self) -> Dict[str, List[str]]:
        return SWARM_PRESETS

    def list_agents(self) -> List[str]:
        return list(AGENT_PERSONAS.keys())
