import React, { useState } from 'react'
import './Upload.css'

function Upload() {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [uploadStatus, setUploadStatus] = useState(null)

  const handleFileChange = (e) => {
    setFile(e.target.files[0])
    setUploadStatus(null)
  }

  const handleUpload = async (e) => {
    e.preventDefault()
    if (!file) return

    setUploading(true)
    
    // Simulate upload
    setTimeout(() => {
      setUploading(false)
      setUploadStatus({
        success: true,
        message: 'RFQ uploaded successfully!',
        rfqId: 'RFQ-2024-005',
        redirectUrl: '/rfq/RFQ-2024-005'
      })
    }, 2000)
  }

  return (
    <div className="upload-container">
      <h1 className="upload-title">Upload RFQ</h1>
      
      <div className="upload-card">
        <form onSubmit={handleUpload} className="upload-form">
          <div className="file-input-wrapper">
            <input 
              type="file" 
              id="file-upload"
              onChange={handleFileChange}
              className="file-input"
            />
            <label htmlFor="file-upload" className="file-label">
              <span className="file-icon">📄</span>
              <span className="file-text">
                {file ? file.name : 'Select or drag & drop an RFQ file'}
              </span>
            </label>
          </div>
          
          <button
            type="submit"
            disabled={!file || uploading}
            className={`upload-button ${uploading ? 'uploading' : ''}`}
          >
            {uploading ? 'Uploading...' : 'Upload RFQ'}
          </button>
        </form>

        {uploadStatus && (
          <div className="upload-status">
            <div className={`status-message ${uploadStatus.success ? 'success' : 'error'}`}>
              <span className="status-icon">{uploadStatus.success ? '✅' : '❌'}</span>
              <span>{uploadStatus.message}</span>
            </div>
            {uploadStatus.rfqId && (
              <div className="rfq-id">
                RFQ ID: <a href={uploadStatus.redirectUrl} className="rfq-link">{uploadStatus.rfqId}</a>
              </div>
            )}
          </div>
        )}
      </div>

      <div className="upload-instructions">
        <h3>Supported formats:</h3>
        <ul className="format-list">
          <li>📧 Email files (.eml, .msg)</li>
          <li>📄 PDF documents (.pdf)</li>
          <li>🖼️ Images (.jpg, .png, .gif)</li>
          <li>📊 Excel sheets (.xlsx, .xls)</li>
          <li>📝 Text files (.txt, .csv)</li>
        </ul>
      </div>
    </div>
  )
}

export default Upload
