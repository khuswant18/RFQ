import React, { useState, useEffect } from "react"
import { Link } from "react-router-dom"
import "./Dashboard.css"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

function Dashboard() {
  const [rfqs, setRfqs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchRfqs = async () => {
      try {
        const res = await fetch(`${API_BASE}/rfq/feed`)
        if (!res.ok) throw new Error("Failed to fetch RFQs")
        const data = await res.json()
        setRfqs(data.rfqs || [])
      } catch (err) {
        console.error("Dashboard fetch error:", err)
        setRfqs([])
      } finally {
        setLoading(false)
      }
    }
    fetchRfqs()
    const interval = setInterval(fetchRfqs, 5000)
    return () => clearInterval(interval)
  }, [])

  const getStatusClass = (status) => {
    switch (status) {
      case "quoted": return "status-quoted"
      case "processing": return "status-processing"
      case "failed": return "status-failed"
      default: return ""
    }
  }

  const total = rfqs.length
  const quoted = rfqs.filter(r => r.status === "quoted").length
  const processing = rfqs.filter(r => r.status === "processing").length
  const failed = rfqs.filter(r => r.status === "failed").length
  const conversionRate = total > 0 ? Math.round((quoted / total) * 100) + "%" : "0%"

  const stats = {
    totalRFQs: total,
    quoted: quoted,
    processing: processing,
    failed: failed,
    conversionRate: conversionRate
  }

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>

      <div className="stats-grid">
        <div className="stat-card">
          <div className="stat-value">{stats.totalRFQs}</div>
          <div className="stat-label">Total RFQs</div>
        </div>
        <div className="stat-card stat-green">
          <div className="stat-value">{stats.quoted}</div>
          <div className="stat-label">Quoted</div>
        </div>
        <div className="stat-card stat-blue">
          <div className="stat-value">{stats.processing}</div>
          <div className="stat-label">Processing</div>
        </div>
        <div className="stat-card stat-red">
          <div className="stat-value">{stats.failed}</div>
          <div className="stat-label">Failed</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{stats.conversionRate}</div>
          <div className="stat-label">Conversion</div>
        </div>
      </div>

      <div className="rfq-table-container">
        <h2 className="table-title">Recent RFQs</h2>
        {loading ? (
          <p style={{ padding: 20 }}>Loading...</p>
        ) : rfqs.length === 0 ? (
          <p style={{ padding: 20 }}>No RFQs yet. Upload one to get started.</p>
        ) : (
          <table className="rfq-table">
            <thead>
              <tr>
                <th>RFQ ID</th>
                <th>Status</th>
                <th>Channel</th>
                <th>File Type</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {rfqs.map(rfq => (
                <tr key={rfq.rfq_id}>
                  <td>
                    <Link to={`/rfq/${rfq.rfq_id}`} className="rfq-link">
                      {rfq.rfq_id?.slice(0, 12)}...
                    </Link>
                  </td>
                  <td>
                    <span className={`status-badge ${getStatusClass(rfq.status)}`}>
                      {rfq.status}
                    </span>
                  </td>
                  <td>{rfq.source_channel || "api"}</td>
                  <td>{rfq.file_type || "text"}</td>
                  <td>{rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "--"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

export default Dashboard
