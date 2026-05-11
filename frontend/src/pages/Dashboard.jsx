import React, { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'

// Mock data for development
const mockRFQs = [
  {
    rfq_id: 'test-001',
    status: 'quoted',
    source_channel: 'whatsapp',
    sender_contact: '+919999999999',
    items: ['12mm Sariya Fe500 10 ton'],
    total_amount: 680000,
    created_at: '2024-05-10T10:00:00'
  },
  {
    rfq_id: 'test-002',
    status: 'processing',
    source_channel: 'email',
    sender_contact: 'buyer@example.com',
    items: ['8mm TMT Bar 5 ton', '10mm TMT Bar 3 ton'],
    total_amount: null,
    created_at: '2024-05-10T11:30:00'
  },
  {
    rfq_id: 'test-003',
    status: 'failed', 
    source_channel: 'api',
    sender_contact: null,
    items: ['Invalid grade Fe999'],
    total_amount: null,
    created_at: '2024-05-10T09:15:00'
  }
]

function Dashboard() {
  const [rfqs, setRfqs] = useState(mockRFQs)
  const [stats, setStats] = useState({
    total: 3,
    quoted: 1,
    processing: 1,
    failed: 1
  })

  return (
    <div className="dashboard">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total RFQs</h3>
          <div className="value">{stats.total}</div>
        </div>
        <div className="stat-card">
          <h3>Quoted</h3>
          <div className="value" style={{color: '#10b981'}}>{stats.quoted}</div>
        </div>
        <div className="stat-card">
          <h3>Processing</h3>
          <div className="value" style={{color: '#f59e0b'}}>{stats.processing}</div>
        </div>
        <div className="stat-card">
          <h3>Failed</h3>
          <div className="value" style={{color: '#ef4444'}}>{stats.failed}</div>
        </div>
      </div>

      <div className="rfq-feed">
        <h2>Recent RFQs</h2>
        {rfqs.map(rfq => (
          <div key={rfq.rfq_id} className="rfq-item">
            <div>
              <div style={{fontWeight: 600, marginBottom: '0.25rem'}}>
                {rfq.rfq_id}
              </div>
              <div style={{fontSize: '0.875rem', color: '#666'}}>
                {rfq.sender_contact || 'Anonymous'}
              </div>
            </div>
            <div>
              <span className={`status-badge ${rfq.status}`}>
                {rfq.status}
              </span>
            </div>
            <div>
              {rfq.total_amount ? (
                <span style={{fontWeight: 600, color: '#667eea'}}>
                  ₹{rfq.total_amount.toLocaleString()}
                </span>
              ) : (
                <span style={{color: '#999'}}>Pending</span>
              )}
            </div>
            <div>
              <Link 
                to={`/rfq/${rfq.rfq_id}`}
                style={{
                  padding: '0.5rem 1rem',
                  backgroundColor: '#667eea',
                  color: 'white',
                  textDecoration: 'none',
                  borderRadius: '6px',
                  fontSize: '0.875rem'
                }}
              >
                View
              </Link>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Dashboard
