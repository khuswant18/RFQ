import React, { useState } from 'react'

function Upload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch('http://localhost:8000/api/v1/ingest/upload', {
        method: 'POST',
        body: formData
      })
      
      if (response.ok) {
        const data = await response.json()
        alert('RFQ uploaded successfully! RFQ ID: ' + data.rfq_id)
      } else {
        alert('Upload failed')
      }
    } catch (error) {
      console.error('Error:', error)
      alert('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto', padding: '2rem' }}>
      <h2>Upload RFQ</h2>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: '1rem' }}>
          <input
            type="file"
            onChange={handleFileChange}
            accept=".jpg,.jpeg,.png,.pdf,.docx,.xlsx,.txt"
            style={{ padding: '0.5rem', border: '1px solid #ddd', borderRadius: '4px', width: '100%' }}
          />
        </div>
        <button
          type="submit"
          disabled={!file || uploading}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: '#667eea',
            color: 'white',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '1rem',
            opacity: (!file || uploading) ? 0.6 : 1
          }}
        >
          {uploading ? 'Uploading...' : 'Upload RFQ'}
        </button>
      </form>
    </div>
  )
}

export default Upload
