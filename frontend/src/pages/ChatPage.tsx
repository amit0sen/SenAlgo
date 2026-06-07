import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Loader2 } from 'lucide-react'
import { streamChat } from '../lib/api'

interface Message { role: 'user' | 'assistant'; content: string; loading?: boolean }

const STARTERS = [
  'Analyze RELIANCE.NS using SMC',
  'Backtest SMC strategy on NIFTY 50 for 2 years',
  'What is the Volume Profile POC for BTC-USD?',
  'Generate a trading hypothesis for HDFC Bank',
  'Run walk-forward validation on ema_cross for INFY.NS',
]

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I\'m **SenAlgo**, your AI trading agent by Amit Kumar Sen.\n\nI can analyze markets using SMC, Volume Profile, and Order Flow — and run full backtests. What would you like to explore?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = (msg?: string) => {
    const text = (msg || input).trim()
    if (!text || loading) return
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: text }, { role: 'assistant', content: '', loading: true }])
    setLoading(true)
    let response = ''
    streamChat(text, 'claude-opus-4-6', 'anthropic',
      (chunk) => {
        response += chunk
        setMessages(prev => {
          const copy = [...prev]
          copy[copy.length - 1] = { role: 'assistant', content: response, loading: false }
          return copy
        })
      },
      () => setLoading(false)
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-3 border-b border-surface-border bg-surface-card">
        <h2 className="text-white font-semibold flex items-center gap-2"><Bot size={18} className="text-brand" /> SenAlgo Agent</h2>
        <p className="text-slate-500 text-xs">SMC · Volume · Order Flow · Backtesting</p>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4 scrollbar-thin">
        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div className={`shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${m.role === 'user' ? 'bg-brand' : 'bg-surface-border'}`}>
              {m.role === 'user' ? <User size={14} /> : <Bot size={14} className="text-brand" />}
            </div>
            <div className={`max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
              m.role === 'user' ? 'bg-brand text-white' : 'bg-surface-card text-slate-200 border border-surface-border'}`}>
              {m.loading ? <Loader2 className="animate-spin" size={16} /> : m.content}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Starters */}
      {messages.length <= 1 && (
        <div className="px-6 pb-2 flex flex-wrap gap-2">
          {STARTERS.map(s => (
            <button key={s} onClick={() => send(s)}
              className="text-xs bg-surface-card border border-surface-border px-3 py-1.5 rounded-full text-slate-400 hover:text-white hover:border-brand transition-colors">
              {s}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-6 py-4 border-t border-surface-border">
        <div className="flex gap-3">
          <input
            className="flex-1 bg-surface-card border border-surface-border rounded-lg px-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-brand"
            placeholder="Ask about any symbol, strategy, or market…"
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
            disabled={loading}
          />
          <button onClick={() => send()} disabled={loading || !input.trim()}
            className="bg-brand hover:bg-brand-dark disabled:opacity-40 text-white rounded-lg px-4 transition-colors">
            <Send size={18} />
          </button>
        </div>
      </div>
    </div>
  )
}
