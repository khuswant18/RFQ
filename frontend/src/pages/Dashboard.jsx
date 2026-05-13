import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { FileText, TrendingUp, Clock, AlertTriangle, CheckCircle2, XCircle, Loader2, ArrowRight, RefreshCw } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

function AnimatedCounter({ value, duration = 800 }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    let start = 0
    const step = Math.max(1, Math.ceil(value / (duration / 16)))
    const timer = setInterval(() => {
      start += step
      if (start >= value) { setDisplay(value); clearInterval(timer) }
      else setDisplay(start)
    }, 16)
    return () => clearInterval(timer)
  }, [value, duration])
  return <span>{display}</span>
}

const statusConfig = {
  received: { icon: Clock, color: "blue", label: "Received" },
  processing: { icon: Loader2, color: "amber", label: "Processing" },
  extracted: { icon: FileText, color: "cyan", label: "Extracted" },
  priced: { icon: TrendingUp, color: "violet", label: "Priced" },
  quoted: { icon: CheckCircle2, color: "emerald", label: "Quoted" },
  failed: { icon: XCircle, color: "rose", label: "Failed" },
  review_needed: { icon: AlertTriangle, color: "orange", label: "Review" },
}

function Dashboard() {
  const [rfqs, setRfqs] = useState([])
  const [loading, setLoading] = useState(true)
  const [lastRefresh, setLastRefresh] = useState(new Date())

  const fetchRfqs = async () => {
    try {
      const res = await fetch(`${API_BASE}/rfq/feed`)
      if (!res.ok) throw new Error("Failed")
      const data = await res.json()
      setRfqs(data.rfqs || [])
    } catch (err) {
      console.error("Dashboard fetch:", err)
    } finally {
      setLoading(false)
      setLastRefresh(new Date())
    }
  }

  useEffect(() => {
    fetchRfqs()
    const interval = setInterval(fetchRfqs, 5000)
    return () => clearInterval(interval)
  }, [])

  const total = rfqs.length
  const quoted = rfqs.filter(r => r.status === "quoted").length
  const processing = rfqs.filter(r => ["processing", "extracted", "priced"].includes(r.status)).length
  const failed = rfqs.filter(r => r.status === "failed").length
  const rate = total > 0 ? Math.round((quoted / total) * 100) : 0

  const stats = [
    { label: "Total RFQs", value: total, icon: FileText, gradient: "from-primary-600 to-primary-400" },
    { label: "Quoted", value: quoted, icon: CheckCircle2, gradient: "from-emerald-600 to-emerald-400" },
    { label: "Processing", value: processing, icon: Loader2, gradient: "from-amber-600 to-amber-400" },
    { label: "Failed", value: failed, icon: XCircle, gradient: "from-rose-600 to-rose-400" },
    { label: "Conversion", value: rate, icon: TrendingUp, gradient: "from-accent-600 to-accent-400", suffix: "%" },
  ]

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gradient">Dashboard</h1>
          <p className="text-surface-500 mt-1">Real-time RFQ processing overview</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-surface-600">Updated {lastRefresh.toLocaleTimeString()}</span>
          <button onClick={fetchRfqs} className="p-2 rounded-lg hover:bg-surface-800 transition-colors">
            <RefreshCw size={16} className="text-surface-400" />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="stat-card animate-slide-up" style={{ animationDelay: `${i * 80}ms` }}>
            <div className="flex items-center justify-between">
              <span className="text-xs text-surface-500 uppercase tracking-wider font-semibold">{stat.label}</span>
              <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${stat.gradient} flex items-center justify-center opacity-80`}>
                <stat.icon size={16} className="text-white" />
              </div>
            </div>
            <div className="text-3xl font-bold text-surface-100">
              <AnimatedCounter value={stat.value} />
              {stat.suffix && <span className="text-lg text-surface-400">{stat.suffix}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* RFQ Table */}
      <div className="glass-card overflow-hidden">
        <div className="px-6 py-4 border-b border-surface-800/50 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Recent RFQs</h2>
          <span className="text-xs text-surface-600">{total} total</span>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-primary-500 animate-spin mx-auto mb-3" />
            <p className="text-surface-500">Loading RFQs...</p>
          </div>
        ) : rfqs.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-12 h-12 text-surface-700 mx-auto mb-4" />
            <p className="text-surface-500 text-lg">No RFQs yet</p>
            <p className="text-surface-600 text-sm mt-1">Upload an RFQ to get started</p>
            <Link to="/upload" className="btn-primary inline-flex items-center gap-2 mt-4">
              Upload RFQ <ArrowRight size={16} />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-surface-800/50">
                  <th className="text-left px-6 py-3 text-xs text-surface-500 uppercase tracking-wider font-semibold">RFQ ID</th>
                  <th className="text-left px-6 py-3 text-xs text-surface-500 uppercase tracking-wider font-semibold">Status</th>
                  <th className="text-left px-6 py-3 text-xs text-surface-500 uppercase tracking-wider font-semibold">Channel</th>
                  <th className="text-left px-6 py-3 text-xs text-surface-500 uppercase tracking-wider font-semibold">Type</th>
                  <th className="text-left px-6 py-3 text-xs text-surface-500 uppercase tracking-wider font-semibold">Updated</th>
                  <th className="px-6 py-3"></th>
                </tr>
              </thead>
              <tbody>
                {rfqs.map((rfq, i) => {
                  const sc = statusConfig[rfq.status] || statusConfig.received
                  return (
                    <tr key={rfq.rfq_id}
                      className="border-b border-surface-800/30 hover:bg-surface-800/30 transition-colors animate-slide-up"
                      style={{ animationDelay: `${i * 50}ms` }}>
                      <td className="px-6 py-4">
                        <Link to={`/rfq/${rfq.rfq_id}`} className="font-mono text-sm text-primary-400 hover:text-primary-300 transition-colors">
                          {rfq.rfq_id?.slice(0, 12)}...
                        </Link>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`badge badge-${rfq.status}`}>
                          <sc.icon size={12} className={rfq.status === "processing" ? "animate-spin" : ""} />
                          {sc.label}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-sm text-surface-400">{rfq.source_channel || "api"}</td>
                      <td className="px-6 py-4 text-sm text-surface-400">{rfq.file_type || "text"}</td>
                      <td className="px-6 py-4 text-sm text-surface-500">
                        {rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-6 py-4">
                        <Link to={`/rfq/${rfq.rfq_id}`} className="text-surface-600 hover:text-primary-400 transition-colors">
                          <ArrowRight size={16} />
                        </Link>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
