import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { BarChart2, Bot, TrendingUp, BookOpen, Activity, Layers, Home } from 'lucide-react'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import BacktestPage from './pages/BacktestPage'
import AnalyzePage from './pages/AnalyzePage'
import HypothesesPage from './pages/HypothesesPage'

const NAV = [
  { to: '/', icon: Home, label: 'Home' },
  { to: '/chat', icon: Bot, label: 'Agent' },
  { to: '/analyze', icon: TrendingUp, label: 'Analyze' },
  { to: '/backtest', icon: BarChart2, label: 'Backtest' },
  { to: '/hypotheses', icon: BookOpen, label: 'Hypotheses' },
]

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-surface">
        {/* Sidebar */}
        <aside className="w-16 flex flex-col items-center py-4 gap-1 bg-surface-card border-r border-surface-border">
          <div className="mb-4">
            <Activity className="text-brand" size={28} />
          </div>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 p-2 rounded-lg w-full mx-1 transition-colors ${
                  isActive ? 'bg-brand text-white' : 'text-slate-400 hover:bg-surface-border hover:text-white'
                }`
              }
              title={label}
            >
              <Icon size={20} />
              <span className="text-[10px]">{label}</span>
            </NavLink>
          ))}
        </aside>

        {/* Main content */}
        <main className="flex-1 overflow-auto">
          <Routes>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/analyze" element={<AnalyzePage />} />
            <Route path="/backtest" element={<BacktestPage />} />
            <Route path="/hypotheses" element={<HypothesesPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
