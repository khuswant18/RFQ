import React from 'react'
import { useParams } from 'react-router-dom'

function RFQDetail() {
  const { rfqId } = useParams()

  return (
    <div>
      <h2>RFQ Detail: {rfqId}</h2>
      <p>This page will show the detailed view of an RFQ including:</p>
      <ul>
        <li>Extracted entities and confidence scores</li>
        <li>Cost breakdown</li>
        <li>PDF preview</li>
        <li>Agent execution trace</li>
      </ul>
    </div>
  )
}

export default RFQDetail
