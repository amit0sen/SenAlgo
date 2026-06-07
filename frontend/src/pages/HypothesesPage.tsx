import { useState, useEffect } from 'react'
import { Plus, BookOpen, RefreshCw, Loader2 } from 'lucide-react'
import { listHypotheses, createHypothesis, type Hypothesis } from '../lib/api'

const STATUS_COLOR: Record<string, string> = {
  pending: 'text-yellow-400 bg-yellow-900/30',
  testing: 'text-blue-400 bg-blue-900/30',
  validated: 'text-green-400 bg-green-900/30',
  rejected: 'text-red-400 bg-red-900/30',
}

export default function HypothesesPage() {
  const [hypotheses, setHypotheses] = useState<Hypothesis[]>([])
  const [loading, setLoading] = useState(true)
  const [desc, setDesc] = useState('')
  const [creating, setCreating] = useState(false)
  const [filter, setFilter] = useState('')

  const load = async () => {
    setLoading(true)
    try { const r = await listHypotheses(); setHypotheses(r.hypotheses) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const create = async () => {
    if (!desc.trim()) return
    setCreating(true)
    try { await createHypothesis(desc); setDesc(''); load() }
    finally { setCreating(false) }
  }

  const filtered = filter ? hypotheses.filter(h => h.status === filter) : hypotheses

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h1 className="text-xl font-bold text-white mb-6 flex items-center gap-2">
        <BookOpen className="text-brand" size={22} /> Strategy Hypotheses
      </h1>

      {/* Create */}
      <div className="bg-surface-card border border-surface-border rounded-xl p-4 mb-6">
        <h3 className="text-slate-300 text-sm font-semibold mb-3">New Hypothesis</h3>
        <div className="flex gap-3">
          <input value={desc} onChange={e => setDesc(e.target.value)}
            className="flex-1 bg-surface border border-surface-border rounded-lg px-3 py-2 text-white text-sm focus:border-brand focus:outline-none"
            placeholder="e.g. Add volume filter to SMC — only trade when vol > 1.5x 20-day avg"
            onKeyDown={e => e.key === 'Enter' && create()} />
          <button onClick={create} disabled={creating || !desc.trim()}
            className="bg-brand hover:bg-brand-dark text-white px-4 py-2 rounded-lg text-sm flex items-center gap-2 disabled:opacity-50 transition-colors">
            {creating ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Add
          </button>
        </div>
      </div>

      {/* Filter */}
      <div className="flex gap-2 mb-4">
        {['', 'pending', 'testing', 'validated', 'rejected'].map(s => (
          <button key={s} onClick={() => setFilter(s)}
            className={`px-3 py-1 rounded-full text-xs transition-colors ${filter === s ? 'bg-brand text-white' : 'bg-surface-card text-slate-400 hover:text-white border border-surface-border'}`}>
            {s || 'All'}
          </button>
        ))}
        <button onClick={load} className="ml-auto text-slate-500 hover:text-white">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* List */}
      <div className="space-y-3">
        {loading && <div className="text-center text-slate-500 py-8">Loading…</div>}
        {!loading && filtered.length === 0 && (
          <div className="text-center text-slate-500 py-8">
            No hypotheses yet. Create one above or ask the AI agent to generate one.
          </div>
        )}
        {filtered.map(h => (
          <div key={h.id} className="bg-surface-card border border-surface-border rounded-xl p-4">
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-slate-500 text-xs font-mono">#{h.id}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLOR[h.status] || 'text-slate-400'}`}>
                    {h.status}
                  </span>
                </div>
                <p className="text-slate-200 text-sm">{h.description}</p>
                <div className="text-slate-600 text-xs mt-1">{h.created_at?.slice(0, 16)}</div>
              </div>
              {h.backtest_sharpe !== null && h.backtest_sharpe !== undefined && (
                <div className="text-right shrink-0">
                  <div className={`text-sm font-semibold ${h.backtest_sharpe > 1 ? 'text-green-400' : 'text-red-400'}`}>
                    Sharpe {h.backtest_sharpe?.toFixed(2)}
                  </div>
                  {h.backtest_return !== undefined && (
                    <div className="text-xs text-slate-500">{((h.backtest_return || 0) * 100).toFixed(1)}% return</div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
