import React, { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Upload as UploadIcon, FileText, Image, File, X, CheckCircle2, AlertCircle, Loader2, Type } from "lucide-react"
import { API_BASE } from "../lib/apiBase"

const ACCEPTED_TYPES = {
  "application/pdf": { icon: FileText, label: "PDF", color: "text-rose-600" },
  "image/jpeg": { icon: Image, label: "JPEG", color: "text-blue-600" },
  "image/png": { icon: Image, label: "PNG", color: "text-blue-600" },
  "image/gif": { icon: Image, label: "GIF", color: "text-blue-600" },
  "text/plain": { icon: Type, label: "Text", color: "text-emerald-600" },
}

function UploadPage() {
  const navigate = useNavigate()
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const handleDrop = useCallback((e) => {
    e.preventDefault()
    setDragOver(false)
    const dropped = e.dataTransfer?.files?.[0]
    if (dropped) { setFile(dropped); setResult(null); setError(null) }
  }, [])

  const handleFileChange = (e) => {
    const f = e.target.files?.[0]
    if (f) { setFile(f); setResult(null); setError(null) }
  }

  const handleUploadFile = async () => {
    if (!file) return
    setUploading(true); setError(null); setResult(null)
    const formData = new FormData()
    formData.append("file", file)
    try {
      const res = await fetch(`${API_BASE}/ingest/upload`, { method: "POST", body: formData })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || "Upload failed")
      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setUploading(false)
    }
  }

  const fileInfo = file ? ACCEPTED_TYPES[file.type] || { icon: File, label: "File", color: "text-surface-muted" } : null

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-semibold text-primary">Upload RFQ</h1>
        <p className="text-surface-muted mt-1 text-sm">Upload an RFQ document to initiate processing</p>
      </div>

      {/* File Upload Area */}
      <div className="card p-8 space-y-6">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          className={`relative border border-dashed rounded-input p-12 text-center transition-colors duration-150 cursor-pointer
            ${dragOver ? "border-primary bg-primary/5" : "border-surface-border hover:border-surface-subtle bg-surface-50"}`}>
          <input type="file" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
          {file ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-14 h-14 rounded-lg bg-surface flex items-center justify-center border border-surface-border shadow-sm">
                {fileInfo && <fileInfo.icon size={28} className={fileInfo.color} />}
              </div>
              <p className="text-surface-text font-medium text-sm">{file.name}</p>
              <p className="text-xs text-surface-muted">{(file.size / 1024).toFixed(1)} KB • {fileInfo?.label}</p>
              <button onClick={(e) => { e.stopPropagation(); setFile(null) }}
                className="text-surface-muted hover:text-rose-600 transition-colors mt-2 text-xs flex items-center gap-1 font-medium">
                <X size={14} /> Remove File
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-12 h-12 rounded-lg bg-surface border border-surface-border flex items-center justify-center shadow-subtle">
                <UploadIcon size={24} className="text-surface-muted" />
              </div>
              <p className="text-surface-text text-sm font-medium">Select a file or drag and drop here</p>
              <p className="text-xs text-surface-subtle">PDF, JPEG, PNG, or TXT up to 10MB</p>
            </div>
          )}
        </div>

        <button onClick={handleUploadFile} disabled={!file || uploading} className="btn-primary w-full flex items-center justify-center gap-2">
          {uploading ? <><Loader2 size={16} className="animate-spin" /> Processing Document...</> : <><UploadIcon size={16} /> Process RFQ</>}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="panel p-5 border-l-4 border-l-emerald-500 animate-slide-up">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle2 className="text-emerald-600" size={20} />
            <h3 className="text-base font-semibold text-emerald-800">Processing Initiated</h3>
          </div>
          <p className="text-surface-text text-sm mb-3">The RFQ document has been queued successfully.</p>
          <div className="flex items-center gap-2 mb-4 bg-surface px-3 py-2 rounded-md border border-surface-border">
            <span className="text-xs text-surface-muted uppercase font-semibold tracking-wider">Ref ID:</span>
            <code className="text-sm font-mono text-primary">{result.rfq_id}</code>
          </div>
          <button onClick={() => navigate(`/rfq/${result.rfq_id}`)}
            className="btn-secondary w-full text-sm">
            View Job Status
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="panel p-5 border-l-4 border-l-rose-500 animate-slide-up">
          <div className="flex items-center gap-3">
            <AlertCircle className="text-rose-600" size={20} />
            <div>
              <h3 className="font-semibold text-rose-800 text-sm">Upload Failed</h3>
              <p className="text-surface-text text-sm mt-0.5">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UploadPage
