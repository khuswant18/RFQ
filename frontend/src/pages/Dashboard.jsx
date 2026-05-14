import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import { FileText, TrendingUp, Clock, AlertTriangle, CheckCircle2, XCircle, Loader2, ArrowRight, RefreshCw } from "lucide-react"
import { API_BASE } from "../lib/apiBase"

function AnimatedCounter({ value, duration = 400 }) {
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
  received: { icon: Clock, label: "Received", badge: "received" },
  processing: { icon: Loader2, label: "Processing", badge: "processing" },
  extracted: { icon: FileText, label: "Extracted", badge: "extracted" },
  priced: { icon: TrendingUp, label: "Priced", badge: "priced" },
  quoted: { icon: CheckCircle2, label: "Quoted", badge: "quoted" },
  failed: { icon: XCircle, label: "Failed", badge: "failed" },
  review_needed: { icon: AlertTriangle, label: "Review", badge: "review_needed" },
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
    { label: "Total RFQs", value: total, icon: FileText, bg: "bg-primary/10", color: "text-primary" },
    { label: "Quoted", value: quoted, icon: CheckCircle2, bg: "bg-emerald-50", color: "text-emerald-700" },
    { label: "Processing", value: processing, icon: Loader2, bg: "bg-amber-50", color: "text-amber-700" },
    { label: "Failed", value: failed, icon: XCircle, bg: "bg-rose-50", color: "text-rose-700" },
    { label: "Conversion", value: rate, icon: TrendingUp, bg: "bg-primary-pale", color: "text-primary", suffix: "%" },
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between pb-2">
        <div>
          <h1 className="text-2xl font-semibold text-primary">Dashboard</h1>
          <p className="text-surface-muted mt-1 text-sm">Real-time RFQ processing overview</p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs text-surface-subtle font-medium">Updated {lastRefresh.toLocaleTimeString()}</span>
          <button onClick={fetchRfqs} className="p-2 border border-surface-border rounded-btn hover:bg-surface-panel transition-colors text-surface-muted hover:text-surface-text">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        {stats.map((stat, i) => (
          <div key={i} className="stat-card">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-surface-muted uppercase tracking-wide font-medium">{stat.label}</span>
              <div className={`w-8 h-8 rounded-md ${stat.bg} flex items-center justify-center`}>
                <stat.icon size={16} className={stat.color} />
              </div>
            </div>
            <div className="text-2xl font-bold text-surface-text">
              <AnimatedCounter value={stat.value} />
              {stat.suffix && <span className="text-sm text-surface-muted ml-1">{stat.suffix}</span>}
            </div>
          </div>
        ))}
      </div>

      {/* RFQ Table */}
      <div className="panel overflow-hidden">
        <div className="px-5 py-4 border-b border-surface-border flex items-center justify-between bg-surface-50">
          <h2 className="text-base font-semibold text-surface-text">Recent RFQs</h2>
          <span className="badge badge-received">{total} total</span>
        </div>

        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-8 h-8 text-surface-subtle animate-spin mx-auto mb-3" />
            <p className="text-surface-muted text-sm font-medium">Loading RFQs...</p>
          </div>
        ) : rfqs.length === 0 ? (
          <div className="p-16 text-center border-t border-surface-border">
            <FileText className="w-10 h-10 text-surface-border mx-auto mb-3" />
            <p className="text-surface-text font-medium">No RFQs yet</p>
            <p className="text-surface-muted text-sm mt-1 mb-5">Upload an RFQ to get started with automation</p>
            <Link to="/upload" className="btn-primary inline-flex items-center gap-2">
              Upload RFQ <ArrowRight size={14} />
            </Link>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-surface-panel/50 border-b border-surface-border">
                <tr>
                  <th className="text-left px-5 py-3 text-xs text-surface-muted font-medium w-[20%]">RFQ ID</th>
                  <th className="text-left px-5 py-3 text-xs text-surface-muted font-medium w-[15%]">Status</th>
                  <th className="text-left px-5 py-3 text-xs text-surface-muted font-medium w-[15%]">Channel</th>
                  <th className="text-left px-5 py-3 text-xs text-surface-muted font-medium w-[15%]">Type</th>
                  <th className="text-left px-5 py-3 text-xs text-surface-muted font-medium w-[25%]">Last Updated</th>
                  <th className="px-5 py-3 w-[10%]"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-surface-border">
                {rfqs.map((rfq) => {
                  const sc = statusConfig[rfq.status] || statusConfig.received
                  return (
                    <tr key={rfq.rfq_id} className="hover:bg-surface-panel/30 transition-colors h-12 group">
                      <td className="px-5 text-sm">
                        <Link to={`/rfq/${rfq.rfq_id}`} className="font-mono text-primary hover:underline">
                          {rfq.rfq_id?.slice(0, 8)}...{rfq.rfq_id?.slice(-4)}
                        </Link>
                      </td>
                      <td className="px-5">
                        <span className={`badge badge-${sc.badge}`}>
                          {sc.label}
                        </span>
                      </td>
                      <td className="px-5 text-surface-muted capitalize">{rfq.source_channel || "api"}</td>
                      <td className="px-5 text-surface-muted uppercase">{rfq.file_type || "text"}</td>
                      <td className="px-5 text-surface-muted font-mono text-[13px]">
                        {rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "—"}
                      </td>
                      <td className="px-5 text-right">
                        <Link to={`/rfq/${rfq.rfq_id}`} className="text-surface-subtle hover:text-primary transition-colors opacity-0 group-hover:opacity-100">
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
