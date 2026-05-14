import React, { useState, useEffect, useRef, useMemo } from "react"
import { Upload, FileText, Image as ImageIcon, File, Loader2, CheckCircle2, AlertCircle, MessageSquareText, Send, Download, Paperclip, Sparkles } from "lucide-react"
import { API_BASE } from "../lib/apiBase"

const FILE_TYPES = {
  "application/pdf": { icon: FileText, label: "PDF", color: "text-rose-600" },
  "image/jpeg": { icon: ImageIcon, label: "JPEG", color: "text-blue-600" },
  "image/png": { icon: ImageIcon, label: "PNG", color: "text-blue-600" },
  "image/gif": { icon: ImageIcon, label: "GIF", color: "text-blue-600" },
  "text/plain": { icon: FileText, label: "TXT", color: "text-emerald-600" },
}

function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="max-w-[70%] rounded-2xl px-5 py-3.5 bg-white border border-surface-border shadow-sm">
        <div className="flex items-center gap-1.5">
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  )
}

function formatReply(text) {
  if (!text) return null
  // Convert markdown-like **bold** to <strong>
  const parts = text.split("\n").map((line, i) => {
    const formatted = line
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/⚠️/g, '<span class="text-amber-600">⚠️</span>')
    return <p key={i} className="text-sm text-surface-text leading-relaxed" dangerouslySetInnerHTML={{ __html: formatted }} />
  })
  return <div className="space-y-1">{parts}</div>
}

function ChatUpload() {
  const [messageInput, setMessageInput] = useState("")
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [messages, setMessages] = useState([
    {
      id: "intro",
      role: "assistant",
      text: "👋 Hello! I'm the SRIP RFQ Assistant.\n\nSend me a steel RFQ in plain text or upload a PDF/image, and I'll extract entities, calculate pricing, and generate a professional quote.\n\n**Try:** \"12mm Fe500 sariya 10 ton Surat delivery urgent\"",
    },
  ])
  const endRef = useRef(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  const fileInfo = useMemo(() => {
    if (!file) return null
    return FILE_TYPES[file.type] || { icon: File, label: "FILE", color: "text-surface-muted" }
  }, [file])

  const handlePickFile = (e) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
  }

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleSend = async () => {
    if ((!file && !messageInput.trim()) || loading) return
    setLoading(true)

    const userText = file ? `📎 ${file.name}` : messageInput.trim()
    const userMsgId = `user-${Date.now()}`

    // Add user message
    setMessages(prev => [...prev, { id: userMsgId, role: "user", text: userText }])
    const currentMessage = messageInput.trim()
    const currentFile = file
    setMessageInput("")
    setFile(null)

    try {
      if (currentFile) {
        // File upload flow: upload → poll → get result
        const formData = new FormData()
        formData.append("file", currentFile)
        const res = await fetch(`${API_BASE}/ingest/upload`, { method: "POST", body: formData })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail?.error || data.detail || "Upload failed")

        const rfqId = data.rfq_id

        // Poll for completion
        setMessages(prev => [...prev, {
          id: `poll-${rfqId}`,
          role: "assistant",
          text: "📤 File uploaded. Processing through agents...",
          polling: true,
          rfqId,
        }])

        let pollCount = 0
        const maxPolls = 30
        const pollInterval = setInterval(async () => {
          pollCount++
          try {
            const statusRes = await fetch(`${API_BASE}/rfq/${rfqId}`)
            if (!statusRes.ok) return
            const statusData = await statusRes.json()

            if (statusData.status === "quoted" || statusData.status === "success") {
              clearInterval(pollInterval)
              // Build a summary from the result
              const result = statusData.result || {}
              let summary = "✅ **Quote Ready!**\n\n"
              if (result.quote?.grand_total) {
                summary += `💰 Grand Total: ₹${result.quote.grand_total.toLocaleString()}\n`
              }
              summary += `📄 Quote PDF generated.`

              setMessages(prev => prev.map(msg =>
                msg.id === `poll-${rfqId}`
                  ? { ...msg, text: summary, polling: false, status: "quoted", rfqId }
                  : msg
              ))
              setLoading(false)
            } else if (statusData.status === "failed") {
              clearInterval(pollInterval)
              setMessages(prev => prev.map(msg =>
                msg.id === `poll-${rfqId}`
                  ? { ...msg, text: `❌ Processing failed: ${statusData.error || "Unknown error"}`, polling: false, status: "failed" }
                  : msg
              ))
              setLoading(false)
            } else if (pollCount >= maxPolls) {
              clearInterval(pollInterval)
              setMessages(prev => prev.map(msg =>
                msg.id === `poll-${rfqId}`
                  ? { ...msg, text: "⏰ Processing is taking longer than expected. Check the Dashboard for status.", polling: false }
                  : msg
              ))
              setLoading(false)
            } else {
              // Update status text
              const statusText = {
                processing: "🔄 Processing through agents...",
                extracted: "✅ Entities extracted. Pricing...",
                priced: "💰 Pricing done. Generating quote...",
              }[statusData.status] || `Status: ${statusData.status}`
              setMessages(prev => prev.map(msg =>
                msg.id === `poll-${rfqId}` ? { ...msg, text: statusText } : msg
              ))
            }
          } catch (err) {
            /* ignore poll errors */
          }
        }, 2000)
      } else {
        // Text chat flow: POST /chat → immediate response
        const res = await fetch(`${API_BASE}/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: currentMessage }),
        })
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || "Chat request failed")

        setMessages(prev => [...prev, {
          id: `reply-${data.rfq_id}`,
          role: "assistant",
          text: data.reply,
          rfqId: data.rfq_id,
          status: data.status === "success" ? "quoted" : data.status,
          quoteUrl: data.quote_url,
          needsClarification: data.needs_clarification,
          clarificationQuestions: data.clarification_questions,
          extractedData: data.extracted_data,
          costBreakdown: data.cost_breakdown,
          agentTimings: data.agent_timings,
        }])
        setLoading(false)
      }
    } catch (err) {
      const detail = err?.message || "Request failed"
      const hint = detail === "Failed to fetch" ? `Cannot reach API at ${API_BASE}` : detail
      setMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: "assistant",
        text: `❌ **Error:** ${hint}`,
        isError: true,
      }])
      setLoading(false)
    }
  }

  return (
    <div className="max-w-4xl mx-auto h-[calc(100vh-220px)] flex flex-col animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center border border-primary/20">
          <Sparkles size={20} className="text-primary" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-primary">RFQ Chat</h1>
          <p className="text-sm text-surface-muted">Type your steel RFQ or upload a document for instant quotes.</p>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto rounded-card border border-surface-border bg-gradient-to-b from-surface-50/60 to-white p-5 space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[75%] rounded-2xl px-4 py-3 shadow-sm border transition-all duration-200
              ${msg.role === "user"
                ? "bg-primary text-white border-primary/60"
                : msg.isError
                  ? "bg-rose-50 border-rose-200"
                  : "bg-white border-surface-border"
              }`}>

              {msg.role === "user" ? (
                <p className="text-sm text-white whitespace-pre-wrap">{msg.text}</p>
              ) : (
                formatReply(msg.text)
              )}

              {/* Clarification questions */}
              {msg.needsClarification && msg.clarificationQuestions?.length > 0 && (
                <div className="mt-3 pt-3 border-t border-surface-border/50">
                  <p className="text-xs font-semibold text-surface-muted mb-2">Please provide:</p>
                  <ul className="space-y-1">
                    {msg.clarificationQuestions.map((q, i) => (
                      <li key={i} className="text-xs text-surface-muted flex items-start gap-1.5">
                        <span className="text-primary mt-0.5">•</span> {q}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Quote download */}
              {msg.role === "assistant" && msg.rfqId && (msg.status === "quoted" || msg.quoteUrl) && (
                <div className="mt-3 pt-3 border-t border-surface-border/50 flex items-center gap-3">
                  <a
                    href={msg.quoteUrl || `${API_BASE}/rfq/${msg.rfqId}/quote`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-primary/10 text-primary text-xs font-semibold hover:bg-primary/20 transition-colors"
                  >
                    <Download size={14} /> Download Quote PDF
                  </a>
                  <a
                    href={`/rfq/${msg.rfqId}`}
                    className="inline-flex items-center gap-1.5 text-xs text-surface-muted hover:text-primary transition-colors"
                  >
                    View Details →
                  </a>
                </div>
              )}

              {/* Polling spinner */}
              {msg.polling && (
                <div className="mt-2 flex items-center gap-2 text-xs text-amber-700">
                  <Loader2 size={14} className="animate-spin" /> Processing...
                </div>
              )}

              {/* Agent timings */}
              {msg.agentTimings && (
                <div className="mt-2 pt-2 border-t border-surface-border/30">
                  <div className="flex flex-wrap gap-2">
                    {Object.entries(msg.agentTimings).map(([agent, ms]) => (
                      <span key={agent} className="text-[10px] text-surface-subtle bg-surface-50 px-1.5 py-0.5 rounded">
                        {agent}: {ms}ms
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && <TypingIndicator />}
        <div ref={endRef} />
      </div>

      {/* Input area */}
      <div className="mt-4 rounded-card border border-surface-border bg-surface p-3">
        {/* File attachment preview */}
        {file && (
          <div className="mb-3 flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-50 border border-surface-border">
            {fileInfo && <fileInfo.icon size={16} className={fileInfo.color} />}
            <span className="text-sm text-surface-text flex-1 truncate">{file.name} ({(file.size / 1024).toFixed(1)} KB)</span>
            <button onClick={() => setFile(null)} className="text-xs text-surface-muted hover:text-rose-600 transition-colors">✕</button>
          </div>
        )}

        <div className="flex items-end gap-2">
          {/* Attach button */}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={loading}
            className="flex-shrink-0 w-10 h-10 rounded-xl border border-surface-border bg-surface-50 hover:bg-surface-panel flex items-center justify-center transition-colors disabled:opacity-50"
            title="Attach PDF or Image"
          >
            <Paperclip size={16} className="text-surface-muted" />
          </button>
          <input
            ref={fileInputRef}
            type="file"
            className="hidden"
            accept=".pdf,.png,.jpg,.jpeg,.gif,.txt"
            onChange={handlePickFile}
          />

          {/* Text input */}
          <input
            value={messageInput}
            onChange={(e) => setMessageInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type RFQ (e.g. 12mm Fe500 10 ton Surat)..."
            disabled={loading}
            className="flex-1 h-10 px-4 bg-white border border-surface-border rounded-xl text-sm text-surface-text placeholder:text-surface-subtle focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all disabled:opacity-50"
          />

          {/* Send button */}
          <button
            onClick={handleSend}
            disabled={(!file && !messageInput.trim()) || loading}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-primary hover:bg-primary-dark text-white flex items-center justify-center transition-colors disabled:opacity-40 disabled:cursor-not-allowed active:scale-95"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  )
}

export default ChatUpload
