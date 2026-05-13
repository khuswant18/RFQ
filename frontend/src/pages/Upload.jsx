import React, { useState } from "react"
import "./Upload.css"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

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
    setUploadStatus(null)

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await fetch(`${API_BASE}/ingest/upload`, {
        method: "POST",
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setUploadStatus({
        success: true,
        message: data.message || "RFQ uploaded successfully!",
        rfqId: data.rfq_id,
        redirectUrl: `/rfq/${data.rfq_id}`,
      })
    } catch (err) {
      setUploadStatus({
        success: false,
        message: err.message || "Upload failed",
      })
    } finally {
      setUploading(false)
    }
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
                {file ? file.name : "Select or drag & drop an RFQ file"}
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={!file || uploading}
            className={`upload-button ${uploading ? "uploading" : ""}`}
          >
            {uploading ? "Uploading..." : "Upload RFQ"}
          </button>
        </form>

        {uploadStatus && (
          <div className="upload-status">
            <div className={`status-message ${uploadStatus.success ? "success" : "error"}`}>
              <span className="status-icon">{uploadStatus.success ? "✅" : "❌"}</span>
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
