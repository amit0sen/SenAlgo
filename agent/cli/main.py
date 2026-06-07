"""
SenAlgo CLI — Interactive terminal for SenAlgo by Amit Kumar Sen
"""
from __future__ import annotations
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text
from rich.table import Table
from rich import print as rprint

load_dotenv()
console = Console()


BANNER = """
 ███████╗███████╗███╗   ██╗ █████╗ ██╗      ██████╗  ██████╗ 
 ██╔════╝██╔════╝████╗  ██║██╔══██╗██║     ██╔════╝ ██╔═══██╗
 ███████╗█████╗  ██╔██╗ ██║███████║██║     ██║  ███╗██║   ██║
 ╚════██║██╔══╝  ██║╚██╗██║██╔══██║██║     ██║   ██║██║   ██║
 ███████║███████╗██║ ╚████║██║  ██║███████╗╚██████╔╝╚██████╔╝
 ╚══════╝╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚══════╝ ╚═════╝  ╚═════╝ 
"""

SUBTITLE = "by [bold cyan]Amit Kumar Sen[/bold cyan] — Self-Improving AI Trading Agent"
VERSION = "v1.0.0"


def print_banner():
    console.print(Text(BANNER, style="bold blue"))
    console.print(f"  {SUBTITLE}", justify="center")
    console.print(f"  [dim]{VERSION} | SMC · Order Flow · Volume Profile · Backtesting · Auto Trade[/dim]", justify="center")
    console.print()


def print_help():
    table = Table(title="SenAlgo Commands", show_header=True, header_style="bold cyan")
    table.add_column("Command", style="green")
    table.add_column("Description")
    table.add_row("/analyze SYMBOL", "Full SMC + Volume + Order Flow analysis")
    table.add_row("/backtest SYMBOL [engine]", "Run backtest (engines: smc, vwap_revert, orb, ema_cross)")
    table.add_row("/smc SYMBOL", "Smart Money Concepts analysis")
    table.add_row("/volume SYMBOL", "Volume Profile & VWAP analysis")
    table.add_row("/flow SYMBOL", "Order flow analysis")
    table.add_row("/wf SYMBOL [engine]", "Walk-forward validation")
    table.add_row("/mc SYMBOL [engine]", "Monte Carlo simulation")
    table.add_row("/hypotheses", "List strategy hypotheses")
    table.add_row("/memory", "View agent memory")
    table.add_row("/sessions", "List chat sessions")
    table.add_row("/reset", "Start a new session")
    table.add_row("/help", "Show this help")
    table.add_row("/quit", "Exit SenAlgo")
    console.print(table)
    console.print()
    console.print("[dim]For anything else, just type naturally — the AI agent will handle it.[/dim]")


def handle_slash_command(cmd: str, loop, console: Console) -> bool:
    """Handle /commands. Returns True if handled."""
    parts = cmd.strip().split()
    verb = parts[0].lower()
    args = parts[1:] if len(parts) > 1 else []

    if verb == "/help":
        print_help()
        return True

    if verb == "/quit" or verb == "/exit":
        console.print("[bold red]Goodbye from SenAlgo! — Amit Kumar Sen[/bold red]")
        sys.exit(0)

    if verb == "/reset":
        loop.reset()
        console.print("[green]Session reset.[/green]")
        return True

    if verb == "/hypotheses":
        from src.self_improve.loop import HypothesisRegistry
        registry = HypothesisRegistry()
        hs = registry.list_all()
        if not hs:
            console.print("[dim]No hypotheses yet.[/dim]")
        else:
            t = Table(title="Hypotheses")
            t.add_column("ID")
            t.add_column("Status")
            t.add_column("Description")
            t.add_column("Sharpe")
            for h in hs:
                t.add_row(h.id, h.status, h.description[:60], str(h.backtest_sharpe or ""))
            console.print(t)
        return True

    if verb == "/memory":
        from src.agent.memory import AgentMemory
        mem = AgentMemory()
        entries = mem.list_all()
        if not entries:
            console.print("[dim]Memory is empty.[/dim]")
        else:
            t = Table(title="Agent Memory")
            t.add_column("Key")
            t.add_column("Value")
            for e in entries[:20]:
                t.add_row(e["key"], e["value"][:80])
            console.print(t)
        return True

    if verb == "/sessions":
        from src.core.state import Session
        sessions = Session.list_all()
        t = Table(title="Sessions")
        t.add_column("ID")
        t.add_column("Messages")
        for s in sessions[:10]:
            t.add_row(s["id"], str(s["messages"]))
        console.print(t)
        return True

    # Forward slash commands as natural language
    symbol_commands = {
        "/analyze": f"Run a full analysis (SMC + Volume Profile + Order Flow) for {args[0] if args else 'RELIANCE.NS'}",
        "/smc": f"Run Smart Money Concepts analysis for {args[0] if args else 'RELIANCE.NS'}",
        "/volume": f"Run Volume Profile and VWAP analysis for {args[0] if args else 'RELIANCE.NS'}",
        "/flow": f"Run Order Flow analysis for {args[0] if args else 'RELIANCE.NS'}",
        "/backtest": f"Backtest the {args[1] if len(args) > 1 else 'smc'} strategy on {args[0] if args else 'RELIANCE.NS'}",
        "/wf": f"Run walk-forward validation for {args[0] if args else 'RELIANCE.NS'} using {args[1] if len(args) > 1 else 'smc'} engine",
        "/mc": f"Run Monte Carlo simulation for {args[0] if args else 'RELIANCE.NS'} using {args[1] if len(args) > 1 else 'smc'} engine",
    }
    if verb in symbol_commands:
        message = symbol_commands[verb]
        console.print(f"[dim]→ {message}[/dim]")
        _run_agent(loop, message, console)
        return True

    return False


def _run_agent(loop, message: str, console: Console):
    """Run the agent and stream output."""
    with console.status("[bold green]SenAlgo thinking...[/bold green]", spinner="dots"):
        for chunk in loop.chat(message):
            pass
    # Print final answer
    last = chunk if chunk else ""
    if not last.startswith("[Executed"):
        console.print(Panel(last, title="[bold cyan]SenAlgo[/bold cyan]", border_style="cyan"))
    else:
        console.print(f"[dim]{last}[/dim]")


def main():
    print_banner()

    # Check API keys
    if not os.environ.get("ANTHROPIC_API_KEY") and not os.environ.get("OPENAI_API_KEY"):
        console.print("[yellow]⚠  No API key found. Set ANTHROPIC_API_KEY or OPENAI_API_KEY in .env[/yellow]")
        console.print("[dim]  Running in analysis-only mode (no AI agent).[/dim]")
        console.print()

    provider = os.getenv("SENALGO_LLM_PROVIDER", "anthropic")
    model = os.getenv("SENALGO_MODEL", "claude-opus-4-6")
    console.print(f"[dim]Model: {provider}/{model} | Type /help for commands[/dim]")
    console.print()

    from src.agent.tools import build_tool_registry
    from src.agent.loop import AgentLoop

    registry = build_tool_registry()
    loop = AgentLoop(
        tool_registry=registry,
        llm_provider=provider,
        model=model,
        on_progress=lambda msg: console.print(f"[dim]{msg}[/dim]"),
    )

    print_help()

    while True:
        try:
            user_input = Prompt.ask("\n[bold green]You[/bold green]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[bold red]Goodbye![/bold red]")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            if not handle_slash_command(user_input, loop, console):
                console.print(f"[red]Unknown command: {user_input}. Type /help for help.[/red]")
            continue

        _run_agent(loop, user_input, console)


if __name__ == "__main__":
    main()


# ---------------------------------------------------------------------------
# senalgo init — interactive setup wizard
# ---------------------------------------------------------------------------

PROVIDERS = [
    ("ollama",     "Ollama (local — FREE, no API key needed)  ← RECOMMENDED"),
    ("deepseek",   "DeepSeek (ultra-cheap, GPT-4 quality)"),
    ("groq",       "Groq (fast, free tier available)"),
    ("openrouter", "OpenRouter (200+ models, pay-per-token)"),
    ("gemini",     "Google Gemini (free tier)"),
    ("openai",     "OpenAI GPT-4o"),
    ("anthropic",  "Anthropic Claude"),
    ("dashscope",  "Alibaba DashScope / Qwen"),
    ("zhipu",      "Zhipu AI GLM-4"),
    ("moonshot",   "Moonshot / Kimi"),
]


def run_init() -> None:
    """Interactive first-time setup wizard for SenAlgo."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from pathlib import Path

    console = Console()
    env_path = Path(".env")

    console.print(Panel.fit(
        "[bold cyan]SenAlgo by Amit Kumar Sen[/bold cyan]\n"
        "[white]Interactive Setup Wizard[/white]",
        border_style="cyan"
    ))

    # ── Step 1: LLM provider ──────────────────────────────────────────────
    console.print("\n[bold]Step 1: Choose your AI/LLM provider[/bold]")
    console.print("[dim]Ollama is free and runs locally — no internet needed.[/dim]\n")

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("#", width=3)
    table.add_column("Provider")
    for i, (key, label) in enumerate(PROVIDERS, 1):
        table.add_row(str(i), label)
    console.print(table)

    choice = Prompt.ask(
        "Select provider number [1-10]",
        default="1",
    )
    try:
        idx = int(choice) - 1
        provider_key, provider_label = PROVIDERS[max(0, min(idx, len(PROVIDERS) - 1))]
    except (ValueError, IndexError):
        provider_key, provider_label = PROVIDERS[0]

    console.print(f"[green]✓ Selected: {provider_label}[/green]")

    # ── Step 2: API key (skip for Ollama) ────────────────────────────────
    api_key = ""
    if provider_key != "ollama":
        key_var = {
            "deepseek":   "DEEPSEEK_API_KEY",
            "groq":       "GROQ_API_KEY",
            "openrouter": "OPENROUTER_API_KEY",
            "gemini":     "GEMINI_API_KEY",
            "openai":     "OPENAI_API_KEY",
            "anthropic":  "ANTHROPIC_API_KEY",
            "dashscope":  "DASHSCOPE_API_KEY",
            "zhipu":      "ZHIPU_API_KEY",
            "moonshot":   "MOONSHOT_API_KEY",
        }.get(provider_key, "API_KEY")
        console.print(f"\n[bold]Step 2: Enter your {key_var}[/bold]")
        api_key = Prompt.ask(f"{key_var}", password=True, default="")
    else:
        console.print("\n[green]✓ No API key needed for Ollama![/green]")
        console.print("[dim]Make sure Ollama is running: ollama serve[/dim]")

    # ── Step 3: Fyers live data ───────────────────────────────────────────
    console.print("\n[bold]Step 3: Fyers real-time data feed (optional)[/bold]")
    console.print("[dim]Required for live NSE/BSE tick data. Leave blank to use yfinance (free).[/dim]")
    fyers_client = Prompt.ask("FYERS_CLIENT_ID", default="")
    fyers_token  = Prompt.ask("FYERS_ACCESS_TOKEN", default="", password=True)

    # ── Step 4: Broker ────────────────────────────────────────────────────
    console.print("\n[bold]Step 4: Default broker (optional — paper mode by default)[/bold]")
    broker_options = ["none", "zerodha", "fyers", "dhan", "shoonya", "alpaca", "ibkr", "ccxt_okx"]
    for i, b in enumerate(broker_options, 1):
        console.print(f"  {i}. {b}")
    broker_choice = Prompt.ask("Select broker [1-8]", default="1")
    try:
        broker = broker_options[int(broker_choice) - 1]
    except (ValueError, IndexError):
        broker = "none"

    # ── Write .env ────────────────────────────────────────────────────────
    env_lines = [
        "# SenAlgo configuration — generated by `senalgo init`",
        "# by Amit Kumar Sen\n",
        f"SENALGO_LLM_PROVIDER={provider_key}",
        f"SENALGO_MODEL=",
        f"{'# ' if not api_key else ''}{_key_name(provider_key)}={api_key}",
        "",
        "# Fyers real-time data feed (NSE/BSE live ticks)",
        f"FYERS_CLIENT_ID={fyers_client}",
        f"FYERS_ACCESS_TOKEN={fyers_token}",
        "",
        "# Safety (paper trading is ALWAYS on by default)",
        "SENALGO_PAPER_ONLY=true",
        "SENALGO_MAX_ORDER_VALUE=50000",
        "SENALGO_DAILY_LOSS_CAP=5000",
        "",
        "# Server",
        "SENALGO_HOST=0.0.0.0",
        "SENALGO_PORT=8000",
    ]

    with open(env_path, "w") as f:
        f.write("\n".join(env_lines) + "\n")

    console.print(f"\n[green]✓ Configuration saved to .env[/green]")
    console.print(Panel.fit(
        "[bold]SenAlgo is ready![/bold]\n\n"
        "Start the CLI:    [cyan]senalgo[/cyan]\n"
        "Start the server: [cyan]senalgo-server[/cyan]\n"
        "Analyze a symbol: [cyan]senalgo /analyze RELIANCE.NS[/cyan]\n"
        "Generate Pine v6: [cyan]senalgo /pine smc_order_blocks[/cyan]",
        border_style="green"
    ))


def _key_name(provider: str) -> str:
    return {
        "deepseek":   "DEEPSEEK_API_KEY",
        "groq":       "GROQ_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini":     "GEMINI_API_KEY",
        "openai":     "OPENAI_API_KEY",
        "anthropic":  "ANTHROPIC_API_KEY",
        "dashscope":  "DASHSCOPE_API_KEY",
        "zhipu":      "ZHIPU_API_KEY",
        "moonshot":   "MOONSHOT_API_KEY",
    }.get(provider, "API_KEY")


def handle_extended_commands(cmd: str, agent) -> bool:
    """Handle new extended slash commands. Returns True if handled."""
    import json, subprocess
    parts = cmd.strip().split()
    command = parts[0].lower()
    arg = " ".join(parts[1:]) if len(parts) > 1 else ""

    if command == "/pine":
        template = arg or "smc_order_blocks"
        result_str = agent.tools.execute("generate_pine_script", {"template": template})
        try:
            data = json.loads(result_str)
            print(f"\n[Pine Script v6 — {data.get('name', template)}]")
            print("─" * 60)
            print(data.get("code", ""))
            print("─" * 60)
            print(f"Available templates: {', '.join(data.get('available_templates', []))}")
        except Exception:
            print(result_str)
        return True

    elif command == "/elliott":
        symbol = arg or "AAPL"
        result_str = agent.tools.execute("elliott_wave_analysis", {"symbol": symbol})
        print(f"\n[Elliott Wave — {symbol}]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/ict":
        symbol = arg or "AAPL"
        result_str = agent.tools.execute("ict_analysis", {"symbol": symbol})
        print(f"\n[ICT Analysis — {symbol}]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/crt":
        symbol = arg or "AAPL"
        result_str = agent.tools.execute("crt_analysis", {"symbol": symbol})
        print(f"\n[Candle Range Theory — {symbol}]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/factors":
        symbol = arg or "AAPL"
        result_str = agent.tools.execute("multi_factor_analysis", {"symbol": symbol})
        print(f"\n[Multi-Factor Alpha — {symbol}]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/shadow":
        if not arg:
            print("[Usage] /shadow <path/to/tradebook.csv> [broker]")
            return True
        file_parts = arg.split()
        file_path = file_parts[0]
        broker = file_parts[1] if len(file_parts) > 1 else "generic"
        result_str = agent.tools.execute("analyze_shadow_account", {"file_path": file_path, "broker": broker})
        try:
            data = json.loads(result_str)
            print(f"\n[Shadow Account Analysis — {file_path}]")
            print(json.dumps(data, indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/swarm":
        topic = arg or "Analyze current market conditions"
        result_str = agent.tools.execute("swarm_analysis", {"topic": topic})
        print(f"\n[Multi-Agent Swarm — {topic}]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    elif command == "/brokers":
        result_str = agent.tools.execute("list_broker_connectors", {})
        print("\n[Supported Broker Connectors]")
        try:
            print(json.dumps(json.loads(result_str), indent=2))
        except Exception:
            print(result_str)
        return True

    return False
