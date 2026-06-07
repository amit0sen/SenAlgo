"""
SenAlgo FastAPI Server
by Amit Kumar Sen

REST API + SSE streaming for the SenAlgo trading agent.
Endpoints:
  POST /chat          — send a message to the agent (SSE stream)
  GET  /sessions      — list chat sessions
  POST /analyze       — quick SMC + volume + order flow analysis
  POST /backtest      — run a backtest
  GET  /positions     — broker positions
  GET  /hypotheses    — strategy hypothesis registry
  GET  /health        — health check
"""
from __future__ import annotations
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lazy imports (avoid heavy startup cost)
_tool_registry = None
def get_registry():
    global _tool_registry
    if _tool_registry is None:
        from src.agent.tools import build_tool_registry
        _tool_registry = build_tool_registry()
    return _tool_registry

app = FastAPI(
    title="SenAlgo API",
    description="SenAlgo by Amit Kumar Sen — Self-Improving AI Trading Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("SENALGO_CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    model: str = "claude-opus-4-6"
    provider: str = "anthropic"


class AnalyzeRequest(BaseModel):
    symbol: str
    interval: str = "1d"
    period: str = "1y"


class BacktestRequest(BaseModel):
    symbol: str
    engine: str = "smc"
    interval: str = "1d"
    period: str = "2y"
    initial_capital: float = 100_000


class HypothesisRequest(BaseModel):
    description: str
    strategy_code: str = ""


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "SenAlgo by Amit Kumar Sen",
        "version": "1.0.0",
    }


@app.post("/chat")
async def chat(req: ChatRequest):
    """Stream agent responses via SSE."""
    from src.agent.loop import AgentLoop

    async def event_generator() -> AsyncGenerator[str, None]:
        loop = AgentLoop(
            tool_registry=get_registry(),
            llm_provider=req.provider,
            model=req.model,
        )
        try:
            for chunk in loop.chat(req.message):
                data = json.dumps({"type": "content", "text": chunk})
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)
        except Exception as e:
            logger.exception("Chat error")
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return EventSourceResponse(event_generator())


@app.get("/sessions")
async def list_sessions():
    from src.core.state import Session
    return {"sessions": Session.list_all()}


@app.post("/analyze")
async def analyze(req: AnalyzeRequest):
    """Full SMC + Volume + Order Flow analysis for a symbol."""
    from src.market_data.loader import load_ohlcv
    from src.smc.engine import SMCEngine
    from src.volume_profile.engine import VolumeProfileEngine
    from src.order_flow.engine import OrderFlowEngine

    df = load_ohlcv(req.symbol, interval=req.interval, period=req.period)
    if df.empty:
        raise HTTPException(404, f"No data for {req.symbol}")

    smc_result = SMCEngine().analyze(df)
    vp_result = VolumeProfileEngine().analyze(df)
    of_result = OrderFlowEngine().analyze(df)

    return {
        "symbol": req.symbol,
        "interval": req.interval,
        "bars": len(df),
        "latest_price": float(df["close"].iloc[-1]),
        "smc": smc_result.to_dict(),
        "volume_profile": vp_result.to_dict(),
        "order_flow": of_result.to_dict(),
    }


@app.post("/backtest")
async def run_backtest(req: BacktestRequest):
    """Run a strategy backtest."""
    from src.market_data.loader import load_ohlcv
    from src.backtest.engine import BacktestEngine
    from src.backtest.signals import BUILT_IN_ENGINES

    df = load_ohlcv(req.symbol, interval=req.interval, period=req.period)
    if df.empty:
        raise HTTPException(404, f"No data for {req.symbol}")

    eng_class = BUILT_IN_ENGINES.get(req.engine)
    if not eng_class:
        raise HTTPException(400, f"Unknown engine: {req.engine}. Available: {list(BUILT_IN_ENGINES)}")

    runner = BacktestEngine(initial_capital=req.initial_capital)
    result = runner.run(df, eng_class(), symbol=req.symbol)
    mc = runner.monte_carlo(result.trades)

    return {**result.to_dict(), "monte_carlo": mc}


@app.get("/hypotheses")
async def list_hypotheses(status: Optional[str] = None):
    from src.self_improve.loop import HypothesisRegistry
    registry = HypothesisRegistry()
    hypotheses = registry.list_all(status=status)
    return {"count": len(hypotheses), "hypotheses": [h.to_dict() for h in hypotheses]}


@app.post("/hypotheses")
async def create_hypothesis(req: HypothesisRequest):
    from src.self_improve.loop import HypothesisRegistry
    registry = HypothesisRegistry()
    h = registry.create(description=req.description, strategy_code=req.strategy_code)
    return h.to_dict()


@app.get("/positions")
async def get_positions(broker: str = "paper"):
    """Get current broker positions."""
    if broker == "paper":
        return {"broker": "paper", "positions": [], "message": "No live broker connected"}
    return {"broker": broker, "positions": [], "message": "Connect a broker in .env"}


def start():
    import uvicorn
    host = os.getenv("SENALGO_HOST", "0.0.0.0")
    port = int(os.getenv("SENALGO_PORT", "8000"))
    uvicorn.run("api_server:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    start()
