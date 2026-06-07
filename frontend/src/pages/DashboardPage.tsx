import { Activity, TrendingUp, BarChart2, BookOpen, Zap } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const FEATURES = [
  { icon: TrendingUp, title: 'SMC Analysis', desc: 'Order Blocks · BOS/CHOCH · FVG · Liquidity · Premium/Discount', to: '/analyze', color: 'text-blue-400' },
  { icon: BarChart2, title: 'Volume Profile', desc: 'POC · VAH/VAL · VWAP Bands · Cumulative Delta · Market Profile', to: '/analyze', color: 'text-green-400' },
  { icon: Activity, title: 'Order Flow', desc: 'Footprint · Delta · Absorption · Imbalances · Divergence', to: '/analyze', color: 'text-purple-400' },
  { icon: Zap, title: 'Backtesting', desc: 'Walk-Forward · Monte Carlo · Sharpe · Sortino · Max DD', to: '/backtest', color: 'text-yellow-400' },
  { icon: BookOpen, title: 'Self-Improve', desc: 'Hypothesis registry · AI-generated strategies · Auto validation', to: '/hypotheses', color: 'text-red-400' },
]

export default function DashboardPage() {
  return (
    <div className="p-8 max-w-5xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold text-white mb-2">
          <span className="text-brand">Sen</span>Algo
        </h1>
        <p className="text-slate-400 text-lg">Self-Improving AI Trading Agent</p>
        <p className="text-slate-500 text-sm mt-1">by <span className="text-cyan-400">Amit Kumar Sen</span></p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {FEATURES.map(({ icon: Icon, title, desc, to, color }) => (
          <NavLink key={title} to={to}
            className="bg-surface-card border border-surface-border rounded-xl p-5 hover:border-brand transition-colors group">
            <Icon className={`${color} mb-3`} size={28} />
            <h3 className="text-white font-semibold mb-1 group-hover:text-brand transition-colors">{title}</h3>
            <p className="text-slate-500 text-xs leading-relaxed">{desc}</p>
          </NavLink>
        ))}
        <NavLink to="/chat"
          className="bg-gradient-to-br from-brand/20 to-blue-900/20 border border-brand/40 rounded-xl p-5 hover:border-brand transition-colors group col-span-full md:col-span-1 lg:col-span-1">
          <Activity className="text-brand mb-3" size={28} />
          <h3 className="text-white font-semibold mb-1">AI Agent Chat</h3>
          <p className="text-slate-400 text-xs leading-relaxed">
            Natural language trading research. Ask anything about markets, strategies, or analysis.
          </p>
        </NavLink>
      </div>

      <div className="text-center text-slate-600 text-xs">
        SMC · Order Flow · Volume Profile · Backtesting · Auto Trade · Self-Improving AI
      </div>
    </div>
  )
}
