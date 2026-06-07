# Push SenAlgo to GitHub — Step-by-Step

## Step 1: Create the GitHub Repository

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name:** `SenAlgo`
   - **Description:** `Self-Improving AI Trading Agent by Amit Kumar Sen — SMC · Order Flow · Volume Profile · Backtesting`
   - **Visibility:** Public (recommended) or Private
   - ❌ Do NOT check "Add README" (we already have one)
3. Click **Create repository**

---

## Step 2: Open PowerShell in the SenAlgo folder

Right-click on the `senalgo` folder → **Open in Terminal** (or open PowerShell and cd to it):

```powershell
cd "C:\Users\Amit Kumar Sen\OneDrive\Documents\Claude\Projects\Self Improve AI trading Agent\senalgo"
```

---

## Step 3: Initialize Git and Push

Paste these commands one by one:

```powershell
git init
git config user.name "Amit Kumar Sen"
git config user.email "akperson44@gmail.com"
git branch -M main
git add .
git commit -m "Initial commit: SenAlgo v1.0.0 by Amit Kumar Sen

Self-improving AI trading agent featuring:
- SMC Engine: Order Blocks, BOS/CHOCH, FVG, Liquidity
- Volume Profile: POC, VAH, VAL, VWAP bands, Delta
- Order Flow: Footprint, Cumulative Delta, Absorption
- Backtesting: Multi-asset, Walk-forward, Monte Carlo
- AI Agent Loop: Claude/GPT-4 powered ReAct agent
- Self-Improvement: Hypothesis registry and validation
- Broker Connectors: Zerodha, Alpaca (paper + live)
- FastAPI backend + React 19 frontend"

git remote add origin https://github.com/AmitKumarSen/SenAlgo.git
git push -u origin main
```

> **Note:** Replace `AmitKumarSen` with your actual GitHub username if different.

---

## Step 4: Set up .env

```powershell
copy .env.example .env
notepad .env   # add your API keys
```

---

## Step 5: Run SenAlgo

```powershell
pip install -e ".[dev]"
senalgo              # interactive CLI
# OR
senalgo-server       # API on :8000 + frontend on :5173
```
