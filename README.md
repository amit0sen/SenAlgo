<div align="center">

# SenAlgo
### AI Trading Agent by Amit Kumar Sen

*Self-improving multi-strategy AI trading research agent*

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![Pine Script v6](https://img.shields.io/badge/Pine%20Script-v6-brightgreen.svg)](https://tradingview.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-amit0sen%2FSenAlgo-black.svg)](https://github.com/amit0sen/SenAlgo)

</div>

---

## ✨ Features

### 🤖 AI Agent (12+ LLM Providers — No Key Required)
| Provider | Key Needed | Notes |
|----------|-----------|-------|
| **Ollama** (default) | ❌ No | Local, completely free |
| DeepSeek | ✅ Yes | Ultra-cheap, GPT-4 quality |
| Groq | ✅ Yes | Fast, free tier |
| OpenRouter | ✅ Yes | 200+ models |
| Gemini | ✅ Yes | Free tier available |
| OpenAI | ✅ Yes | GPT-4o / o1 |
| Anthropic | ✅ Yes | Claude |
| DashScope/Qwen, Zhipu, Moonshot, MiniMax, Z.ai | ✅ Yes | Chinese providers |

### 📊 Strategy Library (All Strategies — Not Just SMC)
- **Smart Money Concepts (SMC)**: Order Blocks, BOS/CHOCH, FVG, Liquidity sweeps
- **ICT Concepts**: Power of 3, Kill Zones, OTE, Breaker Blocks, NWOG/NDOG
- **Elliott Wave Theory**: 5-wave impulse, ABC corrective, Fibonacci projections
- **Candle Range Theory (CRT)**: Forming → Raid → Fill — intra-candle manipulation
- **Opening Range Breakout (ORB)**: First 15/30/60-min range, breakout entries
- **Price Action**: Pin bars, Engulfing, Inside bars, S/R levels
- **Auction Market Theory**: Volume Profile, POC/VAH/VAL, Market Profile
- **Order Flow**: Footprint, Cumulative Delta, Absorption, Imbalances
- **Momentum**: RSI divergence, MACD, Stochastic, Williams %R
- **Mean Reversion**: Bollinger Bands, VWAP deviation, Z-score
- **Multi-Factor Quant**: 452+ factors (Alpha101, GTJA191, Qlib158, FF5+Carhart)

### 📡 Market Data (100% Free — No API Keys)
| Source | Market | Key |
|--------|--------|-----|
| yfinance | US/HK/NSE/BSE | ❌ None |
| ccxt (OKX public) | Crypto | ❌ None |
| AKShare | A-shares | ❌ None |
| **Fyers WebSocket** | NSE/BSE live ticks | ✅ Fyers account |

### 🏦 Broker Connectors (10+)
| Region | Brokers |
|--------|---------|
| **India** | Zerodha Kite, **Fyers**, Dhan, Shoonya/Finvasia |
| **US** | Alpaca, Robinhood, Interactive Brokers (IBKR) |
| **Global** | Tiger Brokers, Futu/Moomoo, Longbridge |
| **Crypto** | Binance, OKX, **CCXT (100+ exchanges)** |

### 📈 Pine Script v6 Generator
Generate complete, compilable TradingView Pine Script **version 6** code:
- SMC Order Blocks indicator
- ICT Kill Zones + OTE
- Elliott Wave counter
- Volume Profile + VWAP (3 std dev bands)
- Opening Range Breakout strategy
- Candle Range Theory (CRT) indicator
- Custom strategies from natural language

### 🧠 Self-Improvement Loop
- **Hypothesis Registry**: generate → backtest → validate → improve
- **Shadow Account**: analyze your broker trade journal CSV exports
- **Multi-agent Swarm**: 14 specialist AI agents debate and reach consensus
  - Investment Committee | Quant Desk | Crypto Desk | India F&O Desk
  - SMC Team | Macro Desk | Elliott Wave Council | Full Committee

### 🔙 Backtesting Engine
- Event-driven, walk-forward validation, Monte Carlo simulation
- Metrics: Sharpe, Sortino, Calmar, MaxDD, Win Rate, Profit Factor, VaR95

---

## 🚀 Quick Start

### Option A: Ollama (Completely Free — No API Key)
```bash
# 1. Install Ollama
# Visit https://ollama.com and install

# 2. Pull a model
ollama pull qwen2.5:14b

# 3. Install SenAlgo
cd senalgo
pip install -e ".[dev]"

# 4. Run interactive setup
senalgo init

# 5. Start
senalgo
```

### Option B: DeepSeek (Ultra-Cheap)
```bash
pip install -e ".[dev]"
echo "SENALGO_LLM_PROVIDER=deepseek" > .env
echo "DEEPSEEK_API_KEY=your_key" >> .env
senalgo
```

### Option C: Any other provider
```bash
senalgo init   # interactive wizard — pick any provider
```

---

## 💬 CLI Commands

```
senalgo               Start the interactive chat agent
senalgo init          Interactive setup wizard (LLM + broker + data feed)
senalgo-server        Start the FastAPI backend server

Slash commands inside chat:
  /analyze SYMBOL     Full analysis (SMC + VP + OF + ICT)
  /smc SYMBOL         SMC-only analysis
  /elliott SYMBOL     Elliott Wave analysis
  /ict SYMBOL         ICT concepts analysis
  /crt SYMBOL         Candle Range Theory
  /factors SYMBOL     Multi-factor alpha analysis
  /pine TEMPLATE      Generate Pine Script v6 code
  /shadow FILE        Analyze trade journal CSV
  /swarm TOPIC        Multi-agent committee analysis
  /backtest SYMBOL    Run backtest
  /wf SYMBOL          Walk-forward validation
  /mc SYMBOL          Monte Carlo simulation
  /hypotheses         List improvement hypotheses
  /brokers            List connected broker accounts
  /memory             Show agent memory
  /sessions           List saved sessions
  /reset              Reset conversation
  /quit               Exit
```

---

## 🌐 Web UI

```bash
# Backend
senalgo-server

# Frontend (open another terminal)
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

---

## 🏦 Live Trading Setup (Indian Markets)

```bash
# Real-time NSE/BSE tick data via Fyers
FYERS_CLIENT_ID=your_client_id
FYERS_ACCESS_TOKEN=your_access_token

# Paper mode is ON by default — set to false only when ready
SENALGO_PAPER_ONLY=true
```

---

## 📊 Pine Script v6 Examples

```bash
# Generate SMC Order Blocks indicator
senalgo /pine smc_order_blocks

# Generate ICT Kill Zones
senalgo /pine ict_kill_zones

# Generate Elliott Wave counter
senalgo /pine elliott_wave

# Generate ORB strategy
senalgo /pine orb_strategy

# Custom strategy
senalgo /pine custom "RSI + EMA crossover"
```

---

## 🤖 Multi-Agent Swarm

```bash
# Ask 4-8 specialist agents and get consensus
senalgo /swarm "Should I go long NIFTY50 this week?"

# Available presets:
# investment_committee — macro + equity + quant + risk
# quant_desk          — quant + volume + order flow + risk
# crypto_desk         — on-chain + defi + order flow + risk
# smc_team            — SMC + ICT + volume + order flow
# india_fno_desk      — F&O + SMC + volume + risk
# full_committee      — all 8 specialists
```

---

## 🛡 Safety

- **Paper mode ON by default** — `SENALGO_PAPER_ONLY=true`
- Kill switch: `touch ~/.senalgo/KILL_SWITCH` → halts all trading instantly
- Daily loss cap enforced per broker
- Audit ledger at `~/.senalgo/audit_ledger.jsonl`

---

## 📁 Project Structure

```
senalgo/
├── agent/src/
│   ├── agent/          # ReAct loop, tools, memory
│   ├── smc/            # Smart Money Concepts engine
│   ├── strategies/     # Elliott Wave, ICT, CRT, Multi-Factor
│   ├── volume_profile/ # POC/VAH/VAL/VWAP engine
│   ├── order_flow/     # Footprint, Delta, Absorption
│   ├── backtest/       # Engine + signal generators
│   ├── brokers/        # Zerodha, Fyers, Dhan, Shoonya, Alpaca, IBKR, Tiger, CCXT
│   ├── pinescript/     # Pine Script v6 generator
│   ├── shadow_account/ # Trade journal analyzer
│   ├── swarm/          # Multi-agent committee
│   ├── self_improve/   # Hypothesis registry
│   ├── market_data/    # yfinance/ccxt/AKShare/Fyers loader
│   └── config/         # Multi-provider LLM config
├── frontend/           # React 19 + TailwindCSS UI
├── cli/                # CLI + senalgo init wizard
├── .env.example        # All config options documented
└── docker-compose.yml  # One-command deployment
```

---

## 📚 Knowledge Base

SenAlgo is trained on strategies from:
- Smart Money Concepts (SMC) methodology
- ICT (Inner Circle Trader) concepts
- Elliott Wave theory + Fibonacci
- Candle Range Theory
- Auction Market Theory (Volume Profile)
- Price Action trading books
- Quantitative finance: Alpha101, GTJA191, Qlib, Fama-French

---

<div align="center">

**SenAlgo** — *Built by Amit Kumar Sen*

[GitHub](https://github.com/amit0sen/SenAlgo) • [Issues](https://github.com/amit0sen/SenAlgo/issues)

</div>
