import React, { useState, useCallback } from "react"
import { useNavigate } from "react-router-dom"
import { Upload as UploadIcon, FileText, Image, File, X, CheckCircle2, AlertCircle, Loader2, Type } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

const ACCEPTED_TYPES = {
  "application/pdf": { icon: FileText, label: "PDF", color: "text-rose-400" },
  "image/jpeg": { icon: Image, label: "JPEG", color: "text-blue-400" },
  "image/png": { icon: Image, label: "PNG", color: "text-blue-400" },
  "image/gif": { icon: Image, label: "GIF", color: "text-blue-400" },
  "text/plain": { icon: Type, label: "Text", color: "text-emerald-400" },
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

  const fileInfo = file ? ACCEPTED_TYPES[file.type] || { icon: File, label: "File", color: "text-surface-400" } : null

  return (
    <div className="max-w-2xl mx-auto space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold text-gradient">Upload RFQ</h1>
        <p className="text-surface-500 mt-1">Upload a file to start processing</p>
      </div>

      {/* File Upload Area */}
      <div className="glass-card p-8 space-y-6">
        <div
          onDrop={handleDrop}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          className={`relative border-2 border-dashed rounded-2xl p-12 text-center transition-all duration-300 cursor-pointer
            ${dragOver ? "border-primary-500 bg-primary-500/5 scale-[1.02]" : "border-surface-700 hover:border-surface-500"}`}>
          <input type="file" onChange={handleFileChange} className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" />
          {file ? (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-primary-500/10 flex items-center justify-center">
                {fileInfo && <fileInfo.icon size={32} className={fileInfo.color} />}
              </div>
              <p className="text-surface-200 font-medium">{file.name}</p>
              <p className="text-sm text-surface-500">{(file.size / 1024).toFixed(1)} KB • {fileInfo?.label}</p>
              <button onClick={(e) => { e.stopPropagation(); setFile(null) }}
                className="text-surface-600 hover:text-rose-400 transition-colors mt-2">
                <X size={16} /> Remove
              </button>
            </div>
          ) : (
            <div className="flex flex-col items-center gap-3">
              <div className="w-16 h-16 rounded-2xl bg-surface-800 flex items-center justify-center">
                <UploadIcon size={32} className="text-surface-500" />
              </div>
              <p className="text-surface-300">Drop your RFQ file here or click to browse</p>
              <p className="text-sm text-surface-600">PDF, Images, Text files accepted</p>
            </div>
          )}
        </div>

        <button onClick={handleUploadFile} disabled={!file || uploading} className="btn-primary w-full flex items-center justify-center gap-2">
          {uploading ? <><Loader2 size={18} className="animate-spin" /> Processing...</> : <><UploadIcon size={18} /> Upload & Process RFQ</>}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="glass-card p-6 border-emerald-500/30 animate-slide-up">
          <div className="flex items-center gap-3 mb-4">
            <CheckCircle2 className="text-emerald-400" size={24} />
            <h3 className="text-lg font-semibold text-emerald-400">RFQ Submitted Successfully</h3>
          </div>
          <p className="text-surface-400 mb-2">{result.message}</p>
          <div className="flex items-center gap-2 mt-4">
            <span className="text-sm text-surface-500">RFQ ID:</span>
            <code className="text-sm font-mono text-primary-400">{result.rfq_id}</code>
          </div>
          <button onClick={() => navigate(`/rfq/${result.rfq_id}`)}
            className="btn-accent mt-4 w-full flex items-center justify-center gap-2">
            View Processing Status →
          </button>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="glass-card p-6 border-rose-500/30 animate-slide-up">
          <div className="flex items-center gap-3">
            <AlertCircle className="text-rose-400" size={24} />
            <div>
              <h3 className="font-semibold text-rose-400">Upload Failed</h3>
              <p className="text-surface-400 text-sm mt-1">{error}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default UploadPage
