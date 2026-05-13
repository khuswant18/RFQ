import React from 'react'
import { BrowserRouter as Router, Routes, Route, Link, useLocation } from 'react-router-dom'
import { LayoutDashboard, Upload, FileText, Activity, Settings, Zap } from 'lucide-react'
import Dashboard from './pages/Dashboard.jsx'
import RFQDetail from './pages/RFQDetail.jsx'
import UploadPage from './pages/Upload.jsx'
import './index.css'

function NavLink({ to, icon: Icon, children }) {
  const location = useLocation()
  const active = location.pathname === to
  return (
    <Link to={to}
      className={`flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300 group
        ${active
          ? 'bg-primary-600/20 text-primary-400 border border-primary-500/30 shadow-neon'
          : 'text-surface-400 hover:text-surface-100 hover:bg-surface-800/50'}`}>
      <Icon size={20} className={`transition-transform duration-300 ${active ? 'text-primary-400' : 'group-hover:scale-110'}`} />
      <span className="font-medium">{children}</span>
    </Link>
  )
}

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface-950/80 backdrop-blur-xl border-r border-surface-800/50 flex flex-col z-40">
      {/* Logo */}
      <div className="p-6 border-b border-surface-800/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center shadow-neon">
            <Zap size={22} className="text-white" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-gradient">SRIP</h1>
            <p className="text-[10px] text-surface-500 uppercase tracking-widest">Smart RFQ Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <p className="text-[10px] text-surface-600 uppercase tracking-widest font-semibold mb-3 px-4">Main Menu</p>
        <NavLink to="/" icon={LayoutDashboard}>Dashboard</NavLink>
        <NavLink to="/upload" icon={Upload}>Upload RFQ</NavLink>

        <p className="text-[10px] text-surface-600 uppercase tracking-widest font-semibold mt-8 mb-3 px-4">System</p>
        <NavLink to="/health" icon={Activity}>Health</NavLink>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-surface-800/50">
        <div className="glass-card-sm p-3 text-center">
          <p className="text-xs text-surface-500">v2.0.0 • Agentic RAG</p>
          <div className="flex items-center justify-center gap-1.5 mt-1">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            <span className="text-[10px] text-emerald-400">System Online</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-surface-950">
        <Sidebar />
        <main className="ml-64 min-h-screen">
          {/* Top bar */}
          <header className="sticky top-0 z-30 bg-surface-950/80 backdrop-blur-xl border-b border-surface-800/30 px-8 py-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-xl font-bold text-surface-100">Smart RFQ Intelligence Pipeline</h2>
                <p className="text-sm text-surface-500">Indian Steel MSME Quotation Automation</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="badge badge-quoted">
                  <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                  Live
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="p-8">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/rfq/:rfqId" element={<RFQDetail />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/health" element={<HealthPage />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

function HealthPage() {
  const [health, setHealth] = React.useState(null)
  React.useEffect(() => {
    fetch('http://localhost:8000/health').then(r => r.json()).then(setHealth).catch(() => setHealth({ status: 'unreachable' }))
  }, [])
  return (
    <div className="animate-fade-in">
      <h1 className="text-2xl font-bold mb-6">System Health</h1>
      <div className="glass-card p-6 max-w-lg">
        {health ? (
          <div className="space-y-3">
            <div className="flex justify-between"><span className="text-surface-400">Status</span><span className={health.status === 'healthy' ? 'text-emerald-400' : 'text-rose-400'}>{health.status}</span></div>
            <div className="flex justify-between"><span className="text-surface-400">Version</span><span>{health.version || '—'}</span></div>
            <div className="flex justify-between"><span className="text-surface-400">Mock Mode</span><span>{health.mock_mode || '—'}</span></div>
          </div>
        ) : <p className="text-surface-500">Checking...</p>}
      </div>
    </div>
  )
}

export default App
