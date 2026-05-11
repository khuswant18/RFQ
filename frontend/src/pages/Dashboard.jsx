import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import './Dashboard.css'

function Dashboard() {
  const [rfqs, setRfqs] = useState([])
  const [loading, setLoading] = useState(true)
  
  // Simulated data for demo purposes
  useEffect(() => {
    const mockData = [
      { id: 'RFQ-2024-001', status: 'quoted', material: '12mm TMT Bar Fe500', quantity: '10 tons', amount: '₹580,000', date: '2024-05-10', client: 'Rajesh Steel' },
      { id: 'RFQ-2024-002', status: 'processing', material: '8mm TMT Bar Fe500', quantity: '5 tons', amount: '--', date: '2024-05-10', client: 'Patel Traders' },
      { id: 'RFQ-2024-003', status: 'quoted', material: '16mm TMT Bar Fe500D', quantity: '15 tons', amount: '₹870,000', date: '2024-05-09', client: 'Gujrat Steels' },
      { id: 'RFQ-2024-004', status: 'failed', material: '20mm TMT Bar Fe550', quantity: '8 tons', amount: '--', date: '2024-05-09', client: 'Sagar Enterprise' }
    ]
    setRfqs(mockData)
    setLoading(false)
  }, [])

  const getStatusClass = (status) => {
    switch (status) {
      case 'quoted': return 'status-quoted'
      case 'processing': return 'status-processing'
      case 'failed': return 'status-failed'
      default: return ''
    }
  }

  const stats = {
    totalRFQs: 24,
    quoted: 18,
    processing: 4,
    failed: 2,
    conversionRate: '75%'
  }

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">Dashboard</h1>
      
      {/* Stats Cards */}
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

      {/* Recent RFQs */}
      <div className="rfq-table-container">
        <h2 className="table-title">Recent RFQs</h2>
        <table className="rfq-table">
          <thead>
            <tr>
              <th>RFQ ID</th>
              <th>Material</th>
              <th>Quantity</th>
              <th>Client</th>
              <th>Amount</th>
              <th>Status</th>
              <th>Date</th>
            </tr>
          </thead>
          <tbody>
            {rfqs.map(rfq => (
              <tr key={rfq.id}>
                <td><Link to={`/rfq/${rfq.id}`} className="rfq-link">{rfq.id}</Link></td>
                <td>{rfq.material}</td>
                <td>{rfq.quantity}</td>
                <td>{rfq.client}</td>
                <td className="amount">{rfq.amount}</td>
                <td><span className={`status-badge ${getStatusClass(rfq.status)}`}>{rfq.status}</span></td>
                <td>{rfq.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default Dashboard
