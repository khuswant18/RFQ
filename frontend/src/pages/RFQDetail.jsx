import React, { useState, useEffect } from "react"
import { useParams } from "react-router-dom"
import "./RFQDetail.css"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

function RFQDetail() {
  const { rfqId } = useParams()
  const [rfq, setRfq] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchRfq = async () => {
      try {
        const res = await fetch(`${API_BASE}/rfq/${rfqId}`)
        if (!res.ok) throw new Error("RFQ not found")
        const data = await res.json()
        setRfq(data)
      } catch (err) {
        setError(err.message || "Failed to load RFQ")
      } finally {
        setLoading(false)
      }
    }
    fetchRfq()
  }, [rfqId])

  if (loading) return <div className="rfq-detail-container"><p>Loading...</p></div>
  if (error) return <div className="rfq-detail-container"><p className="status-message error">{error}</p></div>
  if (!rfq) return <div className="rfq-detail-container"><p>RFQ not found</p></div>

  const result = rfq.result || {}
  const pricing = result.pricing || {}
  const gst = result.gst || {}
  const quote = result.quote || {}

  const materialCost = pricing.total_subtotal || 0
  const logisticsCost = pricing.item_costs?.reduce((sum, i) => sum + (i.logistics_cost || 0), 0) || 0
  const marginTotal = pricing.item_costs?.reduce((sum, i) => sum + (i.margin_amount || 0), 0) || 0
  const gstAmount = gst.total_gst || 0
  const grandTotal = materialCost + logisticsCost + marginTotal + gstAmount

  return (
    <div className="rfq-detail-container">
      <h1 className="detail-title">RFQ Detail: {rfq.rfq_id}</h1>

      <div className="detail-card">
        <div className="detail-info">
          <p><strong>Status:</strong> <span className={`status-${rfq.status}`}>{rfq.status}</span></p>
          <p><strong>Source:</strong> {rfq.source_channel || "api"}</p>
          <p><strong>File Type:</strong> {rfq.file_type || "text"}</p>
          <p><strong>Sender:</strong> {rfq.sender_contact || "N/A"}</p>
          <p><strong>Created At:</strong> {rfq.created_at ? new Date(rfq.created_at).toLocaleString() : "--"}</p>
          <p><strong>Updated At:</strong> {rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "--"}</p>
        </div>

        <div className="quote-breakdown">
          <h2>Quote Breakdown</h2>
          <div className="breakdown-row">
            <span>Material Cost:</span>
            <span>₹{materialCost.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>Logistics:</span>
            <span>₹{logisticsCost.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>Margin:</span>
            <span>₹{marginTotal.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>GST ({gst.gst_rate_pct || 18}%):</span>
            <span>₹{gstAmount.toLocaleString()}</span>
          </div>
          <div className="breakdown-row total">
            <span>Grand Total:</span>
            <span>₹{grandTotal.toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="action-buttons">
        {quote.pdf_path && (
          <a href={`${API_BASE}/rfq/${rfqId}/quote`} className="btn btn-primary" target="_blank" rel="noopener noreferrer">
            Download Quote PDF
          </a>
        )}
        {rfq.sender_contact && (
          <button className="btn btn-secondary">Send via WhatsApp</button>
        )}
        <button className="btn btn-danger">Reject RFQ</button>
      </div>
    </div>
  )
}

export default RFQDetail
