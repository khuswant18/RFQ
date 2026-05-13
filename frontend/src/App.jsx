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
      className={`flex items-center gap-3 px-3 py-2.5 rounded-btn transition-colors duration-150 group
        ${active
          ? 'bg-primary/10 text-primary font-medium'
          : 'text-surface-muted hover:text-surface-text hover:bg-surface-panel'}`}>
      <Icon size={18} className={active ? 'text-primary' : 'text-surface-subtle group-hover:text-surface-muted'} />
      <span className="text-sm">{children}</span>
    </Link>
  )
}

function Sidebar() {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 bg-surface border-r border-surface-border flex flex-col z-40">
      {/* Logo */}
      <div className="p-5 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-md bg-primary flex items-center justify-center">
            <Zap size={16} className="text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-primary">SRIP</h1>
            <p className="text-[10px] text-surface-subtle uppercase tracking-widest font-medium">Intelligence</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        <p className="text-[10px] text-surface-subtle uppercase tracking-wider font-semibold mb-2 px-3">Workspace</p>
        <NavLink to="/" icon={LayoutDashboard}>Dashboard</NavLink>
        <NavLink to="/upload" icon={Upload}>Upload RFQ</NavLink>

        <p className="text-[10px] text-surface-subtle uppercase tracking-wider font-semibold mt-6 mb-2 px-3">System</p>
        <NavLink to="/health" icon={Activity}>Health</NavLink>
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-surface-border">
        <div className="panel p-3 text-center">
          <p className="text-xs text-surface-muted font-medium">v2.0.0 • Agentic RAG</p>
          <div className="flex items-center justify-center gap-1.5 mt-1.5">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
            <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wide">System Online</span>
          </div>
        </div>
      </div>
    </aside>
  )
}

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-pageBg">
        <Sidebar />
        <main className="ml-64 min-h-screen flex flex-col">
          {/* Top bar */}
          <header className="sticky top-0 z-30 bg-surface border-b border-surface-border px-8 py-4 flex-shrink-0">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-lg font-semibold text-surface-text">Smart RFQ Intelligence Pipeline</h2>
                <p className="text-sm text-surface-muted mt-0.5">Indian Steel MSME Quotation Automation</p>
              </div>
              <div className="flex items-center gap-3">
                <div className="badge badge-quoted">
                  <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                  Live Connection
                </div>
              </div>
            </div>
          </header>

          {/* Content */}
          <div className="p-8 flex-1 overflow-auto">
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
    fetch('https://rfq-dtvm.onrender.com/health').then(r => r.json()).then(setHealth).catch(() => setHealth({ status: 'unreachable' }))
  }, [])
  return (
    <div className="animate-fade-in max-w-2xl">
      <h1 className="text-2xl font-bold mb-6 text-primary">System Health</h1>
      <div className="panel p-6">
        {health ? (
          <div className="space-y-4">
            <div className="flex justify-between py-2 border-b border-surface-border last:border-0"><span className="text-surface-muted font-medium">Status</span><span className={health.status === 'healthy' ? 'text-emerald-600 font-semibold' : 'text-rose-600 font-semibold'}>{health.status}</span></div>
            <div className="flex justify-between py-2 border-b border-surface-border last:border-0"><span className="text-surface-muted font-medium">Version</span><span className="font-mono text-sm text-surface-text">{health.version || '—'}</span></div>
            <div className="flex justify-between py-2 border-b border-surface-border last:border-0"><span className="text-surface-muted font-medium">Mock Mode</span><span className="font-mono text-sm text-surface-text">{health.mock_mode || '—'}</span></div>
          </div>
        ) : <p className="text-surface-subtle">Checking...</p>}
      </div>
    </div>
  )
}

export default App
