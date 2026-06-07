import { useState } from 'react'
import { Search, TrendingUp, BarChart2, Activity, AlertCircle, Loader2 } from 'lucide-react'
import { analyze, type AnalyzeResult } from '../lib/api'

const INTERVALS = ['1m','5m','15m','30m','1h','4h','1d','1wk']
const PERIODS = ['1mo','3mo','6mo','1y','2y','max']

function MetricCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-surface-card border border-surface-border rounded-lg p-3">
      <div className="text-slate-500 text-xs mb-1">{label}</div>
      <div className="text-white font-semibold text-sm">{value}</div>
      {sub && <div className="text-slate-500 text-xs mt-0.5">{sub}</div>}
    </div>
  )
}

export default function AnalyzePage() {
  const [symbol, setSymbol] = useState('RELIANCE.NS')
  const [interval, setInterval] = useState('1d')
  const [period, setPeriod] = useState('1y')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<AnalyzeResult | null>(null)
  const [error, setError] = useState('')

  const run = async () => {
    setLoading(true); setError(''); setResult(null)
    try { setResult(await analyze(symbol, interval, period)) }
    catch (e: any) { setError(e.message || 'Analysis failed') }
    finally { setLoading(false) }
  }

  const smc = result?.smc as any
  const vp = result?.volume_profile as any
  const of_ = result?.order_flow as any

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <h1 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
        <TrendingUp className="text-brand" size={22} /> Market Analysis
      </h1>

      {/* Controls */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <input value={symbol} onChange={e => setSymbol(e.target.value.toUpperCase())}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none w-40"
          placeholder="RELIANCE.NS" />
        <select value={interval} onChange={e => setInterval(e.target.value)}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none">
          {INTERVALS.map(i => <option key={i}>{i}</option>)}
        </select>
        <select value={period} onChange={e => setPeriod(e.target.value)}
          className="bg-surface-card border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none">
          {PERIODS.map(p => <option key={p}>{p}</option>)}
        </select>
        <button onClick={run} disabled={loading}
          className="bg-brand hover:bg-brand-dark text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 transition-colors">
          {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
          Analyze
        </button>
      </div>

      {error && <div className="flex items-center gap-2 text-red-400 text-sm mb-4"><AlertCircle size={16}/>{error}</div>}

      {result && (
        <div className="space-y-6">
          {/* Header */}
          <div className="bg-surface-card border border-surface-border rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-white font-bold text-lg">{result.symbol}</h2>
                <p className="text-slate-500 text-xs">{result.bars} bars · {interval} · {period}</p>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold text-white">{result.latest_price?.toFixed(2)}</div>
                <div className="text-slate-500 text-xs">Latest Close</div>
              </div>
            </div>
          </div>

          {/* SMC */}
          <section>
            <h3 className="text-slate-300 font-semibold mb-3 flex items-center gap-2"><TrendingUp size={16} className="text-blue-400"/>Smart Money Concepts</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              <MetricCard label="Trend" value={smc?.trend?.toUpperCase?.()} />
              <MetricCard label="Active Bullish OBs" value={smc?.bullish_obs ?? '—'} />
              <MetricCard label="Active Bearish OBs" value={smc?.bearish_obs ?? '—'} />
              <MetricCard label="Open FVGs" value={smc?.fair_value_gaps ?? '—'} />
              <MetricCard label="Structure Breaks" value={smc?.structure_breaks ?? '—'} />
              <MetricCard label="Liquidity Levels" value={smc?.liquidity_levels ?? '—'} />
              <MetricCard label="Equilibrium" value={smc?.equilibrium?.toFixed?.(2) ?? '—'} />
            </div>
            {smc?.summary && <p className="text-slate-400 text-xs bg-surface-card border border-surface-border rounded-lg px-4 py-3">{smc.summary}</p>}
          </section>

          {/* Volume Profile */}
          <section>
            <h3 className="text-slate-300 font-semibold mb-3 flex items-center gap-2"><BarChart2 size={16} className="text-green-400"/>Volume Profile & VWAP</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              <MetricCard label="POC" value={vp?.poc?.toFixed?.(2) ?? '—'} sub="Point of Control" />
              <MetricCard label="VAH" value={vp?.vah?.toFixed?.(2) ?? '—'} sub="Value Area High" />
              <MetricCard label="VAL" value={vp?.val?.toFixed?.(2) ?? '—'} sub="Value Area Low" />
              <MetricCard label="VWAP" value={vp?.vwap_latest?.toFixed?.(2) ?? '—'} />
            </div>
            {vp?.summary && <p className="text-slate-400 text-xs bg-surface-card border border-surface-border rounded-lg px-4 py-3">{vp.summary}</p>}
          </section>

          {/* Order Flow */}
          <section>
            <h3 className="text-slate-300 font-semibold mb-3 flex items-center gap-2"><Activity size={16} className="text-purple-400"/>Order Flow</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-3">
              <MetricCard label="Cumulative Delta" value={of_?.cumulative_delta?.toFixed?.(0) ?? '—'} />
              <MetricCard label="Delta Divergence" value={of_?.delta_divergence ? '⚠ YES' : 'No'} />
              <MetricCard label="Absorption Zones" value={of_?.absorption_zones ?? '—'} />
              <MetricCard label="Imbalance Zones" value={of_?.imbalance_zones ?? '—'} />
            </div>
            {of_?.summary && <p className="text-slate-400 text-xs bg-surface-card border border-surface-border rounded-lg px-4 py-3">{of_.summary}</p>}
          </section>
        </div>
      )}
    </div>
  )
}
