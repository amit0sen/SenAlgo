import { useState } from 'react'
import { Play, Loader2, AlertCircle } from 'lucide-react'
import { runBacktest, type BacktestResult } from '../lib/api'

const ENGINES = ['smc', 'vwap_revert', 'orb', 'ema_cross']
const PERIODS = ['6mo','1y','2y','3y','5y']

function Metric({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg p-3">
      <div className="text-slate-500 text-xs mb-1">{label}</div>
      <div className={`font-bold text-sm ${good === true ? 'text-green-400' : good === false ? 'text-red-400' : 'text-white'}`}>{value}</div>
    </div>
  )
}

export default function BacktestPage() {
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [engine, setEngine] = useState('smc')
  const [period, setPeriod] = useState('2y')
  const [capital, setCapital] = useState(100000)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try { setResult(await runBacktest(symbol, engine, '1d', period, capital)) }
    catch (e: any) { setError(e.message || 'Backtest failed') }
    finally { setLoading(false) }
  }

  const m = result?.metrics
  const mc = (result as any)?.monte_carlo

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
        <Play className="text-brand" size={22} /> Strategy Backtester
      </h1>

      <div className="flex gap-3 mb-6 flex-wrap">
        <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none w-40"
          placeholder="RELIANCE.NS" />
        <select value={engine} onChange={e => setEngine(e.target.value)}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none">
          {ENGINES.map(e => <option key={e}>{e}</option>)}
        </select>
        <select value={period} onChange={e => setPeriod(e.target.value)}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none">
          {PERIODS.map(p => <option key={p}>{p}</option>)}
        </select>
        <input type="number" value={capital} onChange={e => setCapital(Number(e.target.value))}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none w-32"
          placeholder="Capital" />
        <button onClick={run} disabled={loading}
          className="bg-brand hover:bg-brand-dark text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 transition-colors">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Play size={16} />}
          Run Backtest
        </button>
      </div>

      {error && <div className="flex items-center gap-2 text-red-400 text-sm mb-4"><AlertCircle size={16}/>{error}</div>}

      {result && m && (
        <div className="space-y-6">
          <div className="bg-surface-card border border-surface-border rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-white font-bold">{result.symbol} — {result.engine.toUpperCase()}</h2>
              <span className={`text-sm font-semibold ${(m.total_return || 0) > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {((m.total_return || 0) * 100).toFixed(2)}% Total Return
              </span>
            </div>
            <p className="text-slate-500 text-xs">{result.summary}</p>
          </div>

          <div>
            <h3 className="text-slate-400 text-xs uppercase font-semibold mb-3">Performance Metrics</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Metric label="Sharpe Ratio" value={(m.sharpe || 0).toFixed(2)} good={(m.sharpe || 0) > 1} />
              <Metric label="Sortino Ratio" value={(m.sortino || 0).toFixed(2)} good={(m.sortino || 0) > 1} />
              <Metric label="Calmar Ratio" value={(m.calmar || 0).toFixed(2)} good={(m.calmar || 0) > 0.5} />
              <Metric label="Max Drawdown" value={((m.max_drawdown || 0) * 100).toFixed(1) + '%'} good={(m.max_drawdown || 0) > -0.15} />
              <Metric label="Win Rate" value={((m.win_rate || 0) * 100).toFixed(1) + '%'} good={(m.win_rate || 0) > 0.5} />
              <Metric label="Profit Factor" value={(m.profit_factor || 0) === Infinity ? '∞' : (m.profit_factor || 0).toFixed(2)} good={(m.profit_factor || 0) > 1.5} />
              <Metric label="Total Trades" value={m.total_trades || 0} />
              <Metric label="vs Buy-Hold" value={((result.benchmark_return || 0) * 100).toFixed(2) + '%'} />
              <Metric label="Annualized Return" value={((m.annualized_return || 0) * 100).toFixed(2) + '%'} good={(m.annualized_return || 0) > 0.1} />
              <Metric label="Volatility" value={((m.volatility || 0) * 100).toFixed(2) + '%'} />
              <Metric label="VaR 95%" value={((m.var_95 || 0) * 100).toFixed(2) + '%'} />
              <Metric label="Avg Trade P&L" value={'₹' + (m.avg_trade_pnl || 0).toFixed(0)} good={(m.avg_trade_pnl || 0) > 0} />
            </div>
          </div>

          {mc && (
            <div>
              <h3 className="text-slate-400 text-xs uppercase font-semibold mb-3">Monte Carlo ({(mc as any).probability_profit !== undefined ? `${((mc as any).probability_profit * 100).toFixed(0)}% probability of profit` : ''})</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                <Metric label="Mean Final Equity" value={'₹' + Math.round(mc.mean_final_equity || 0).toLocaleString()} />
                <Metric label="5th Pct Equity" value={'₹' + Math.round(mc.p5_final_equity || 0).toLocaleString()} />
                <Metric label="95th Pct Equity" value={'₹' + Math.round(mc.p95_final_equity || 0).toLocaleString()} />
                <Metric label="Mean Max DD" value={((mc.mean_max_dd || 0) * 100).toFixed(1) + '%'} />
                <Metric label="Worst Max DD" value={((mc.worst_max_dd || 0) * 100).toFixed(1) + '%'} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
