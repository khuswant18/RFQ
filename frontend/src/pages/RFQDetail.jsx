import React from 'react'
import { useParams } from 'react-router-dom'
import './RFQDetail.css'

function RFQDetail() {
  const { rfqId } = useParams()

  // Mock data for the selected RFQ
  const rfq = {
    id: rfqId,
    material: '12mm TMT Bar Fe500',
    quantity: '10 tons',
    client: 'Rajesh Steel',
    status: 'Quoted',
    amount: '₹580,000',
    deliveryLocation: 'Surat, Gujarat',
    createdAt: '2024-05-10 14:30:00',
    quoteDetails: {
      basePrice: 58000,
      weight: 10,
      materialCost: 580000,
      logistics: 5000,
      gst: 18,
      total: 580000 + 5000 * 1.18,
    }
  }

  return (
    <div className="rfq-detail-container">
      <h1 className="detail-title">RFQ Detail: {rfq.id}</h1>
      
      <div className="detail-card">
        <div className="detail-info">
          <p><strong>Material:</strong> {rfq.material}</p>
          <p><strong>Quantity:</strong> {rfq.quantity}</p>
          <p><strong>Client:</strong> {rfq.client}</p>
          <p><strong>Status:</strong> <span className="status-quoted">{rfq.status}</span></p>
          <p><strong>Delivery Location:</strong> {rfq.deliveryLocation}</p>
          <p><strong>Created At:</strong> {rfq.createdAt}</p>
        </div>

        <div className="quote-breakdown">
          <h2>Quote Breakdown</h2>
          <div className="breakdown-row">
            <span>Base Price (per ton):</span>
            <span>₹{rfq.quoteDetails.basePrice.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>Weight (tons):</span>
            <span>{rfq.quoteDetails.weight}</span>
          </div>
          <div className="breakdown-row">
            <span>Material Cost:</span>
            <span>₹{rfq.quoteDetails.materialCost.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>Logistics:</span>
            <span>₹{rfq.quoteDetails.logistics.toLocaleString()}</span>
          </div>
          <div className="breakdown-row">
            <span>GST ({rfq.quoteDetails.gst}%):</span>
            <span>₹{(rfq.quoteDetails.materialCost * (rfq.quoteDetails.gst / 100)).toLocaleString()}</span>
          </div>
          <div className="breakdown-row total">
            <span>Total Amount:</span>
            <span>₹{rfq.quoteDetails.total.toLocaleString()}</span>
          </div>
        </div>
      </div>

      <div className="action-buttons">
        <button className="btn btn-primary">Download Quote PDF</button>
        <button className="btn btn-secondary">Send via WhatsApp</button>
        <button className="btn btn-danger">Reject RFQ</button>
      </div>
    </div>
  )
}

export default RFQDetail
