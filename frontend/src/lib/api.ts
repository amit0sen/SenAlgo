const BASE = ''

export interface AnalyzeResult {
  symbol: string; interval: string; bars: number; latest_price: number
  smc: Record<string, unknown>; volume_profile: Record<string, unknown>; order_flow: Record<string, unknown>
}
export interface BacktestResult {
  symbol: string; engine: string; metrics: Record<string, number>
  total_trades: number; benchmark_return: number; summary: string
  monte_carlo?: Record<string, number>
}
export interface Hypothesis {
  id: string; description: string; status: string
  backtest_sharpe?: number; backtest_return?: number; created_at: string
}

export async function analyze(symbol: string, interval = '1d', period = '1y'): Promise<AnalyzeResult> {
  const r = await fetch(`${BASE}/analyze`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, interval, period }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function runBacktest(
  symbol: string, engine = 'smc', interval = '1d', period = '2y', initial_capital = 100000
): Promise<BacktestResult> {
  const r = await fetch(`${BASE}/backtest`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ symbol, engine, interval, period, initial_capital }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function listHypotheses(status?: string): Promise<{ hypotheses: Hypothesis[] }> {
  const url = status ? `/hypotheses?status=${status}` : '/hypotheses'
  const r = await fetch(`${BASE}${url}`)
  return r.json()
}

export async function createHypothesis(description: string, strategy_code = ''): Promise<Hypothesis> {
  const r = await fetch(`${BASE}/hypotheses`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ description, strategy_code }),
  })
  return r.json()
}

export function streamChat(message: string, model = 'claude-opus-4-6', provider = 'anthropic', onChunk: (text: string) => void, onDone: () => void) {
  const es = new EventSource(`/chat?message=${encodeURIComponent(message)}&model=${model}&provider=${provider}`)
  // Use fetch+ReadableStream for POST
  fetch(`${BASE}/chat`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, model, provider }),
  }).then(async r => {
    const reader = r.body?.getReader()
    const decoder = new TextDecoder()
    if (!reader) { onDone(); return }
    while (true) {
      const { done, value } = await reader.read()
      if (done) { onDone(); break }
      const text = decoder.decode(value)
      for (const line of text.split('\n')) {
        if (line.startsWith('data: ')) {
          try {
            const d = JSON.parse(line.slice(6))
            if (d.type === 'content') onChunk(d.text)
            if (d.type === 'done') { onDone(); return }
          } catch { /* skip */ }
        }
      }
    }
  }).catch(() => onDone())
}
