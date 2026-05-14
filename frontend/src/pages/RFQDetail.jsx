import React, { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Download, Send, Clock, CheckCircle2, XCircle, Loader2, FileText, Cpu, DollarSign, Receipt, ChevronRight, AlertTriangle, Timer } from "lucide-react"
import { API_BASE } from "../lib/apiBase"

const PIPELINE_STEPS = [
  { key: "received", label: "Received", icon: FileText },
  { key: "processing", label: "Processing", icon: Loader2 },
  { key: "extracted", label: "Extracted", icon: Cpu },
  { key: "priced", label: "Priced", icon: DollarSign },
  { key: "quoted", label: "Quoted", icon: Receipt },
]

function StatusStepper({ currentStatus }) {
  const statusOrder = ["received", "processing", "extracted", "priced", "quoted"]
  const currentIdx = statusOrder.indexOf(currentStatus)
  const isFailed = currentStatus === "failed" || currentStatus === "review_needed"

  return (
    <div className="flex items-center gap-1 w-full">
      {PIPELINE_STEPS.map((step, i) => {
        const done = i <= currentIdx && !isFailed
        const active = i === currentIdx && !isFailed
        const StepIcon = step.icon
        return (
          <React.Fragment key={step.key}>
            <div className={`flex items-center gap-2 px-3 py-2 rounded-btn transition-colors duration-150
              ${done ? "bg-emerald-50 text-emerald-700" : active ? "bg-primary/10 text-primary" : "text-surface-subtle"}`}>
              <StepIcon size={14} className={active ? "animate-spin" : ""} />
              <span className="text-xs font-semibold tracking-wide uppercase hidden lg:inline">{step.label}</span>
            </div>
            {i < PIPELINE_STEPS.length - 1 && (
              <ChevronRight size={14} className={done ? "text-emerald-300" : "text-surface-border"} />
            )}
          </React.Fragment>
        )
      })}
      {isFailed && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-btn bg-rose-50 text-rose-700 ml-2">
          {currentStatus === "failed" ? <XCircle size={14} /> : <AlertTriangle size={14} />}
          <span className="text-xs font-semibold tracking-wide uppercase">{currentStatus === "failed" ? "Failed" : "Review"}</span>
        </div>
      )}
    </div>
  )
}

function CostRow({ label, value, highlight }) {
  return (
    <div className={`flex justify-between py-3 ${highlight ? "border-t border-surface-border mt-1 bg-surface-50 -mx-6 px-6 -mb-6 pb-6 pt-4 rounded-b-card" : ""}`}>
      <span className={highlight ? "text-surface-text font-semibold" : "text-surface-muted"}>{label}</span>
      <span className={highlight ? "text-xl font-bold text-primary" : "text-surface-text font-medium"}>
        ₹{typeof value === "number" ? value.toLocaleString("en-IN", { minimumFractionDigits: 2 }) : value}
      </span>
    </div>
  )
}

function RFQDetail() {
  const { rfqId } = useParams()
  const [rfq, setRfq] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [activeTab, setActiveTab] = useState("overview")

  useEffect(() => {
    const fetchRfq = async () => {
      try {
        const res = await fetch(`${API_BASE}/rfq/${rfqId}`)
        if (!res.ok) throw new Error("RFQ not found")
        setRfq(await res.json())
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }
    fetchRfq()
    const interval = setInterval(fetchRfq, 3000)
    return () => clearInterval(interval)
  }, [rfqId])

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 text-primary animate-spin" /></div>
  if (error) return (
    <div className="panel p-8 text-center max-w-lg mx-auto mt-12">
      <XCircle className="w-10 h-10 text-rose-600 mx-auto mb-3" />
      <p className="text-rose-800 font-medium">{error}</p>
      <Link to="/" className="btn-secondary mt-5 inline-block">← Back to Dashboard</Link>
    </div>
  )
  if (!rfq) return null

  const result = rfq.result || {}
  const pricing = result.pricing || {}
  const gst = result.gst || {}
  const timings = result.agent_timings || {}
  const ner = result.ner || {}
  const ocr = result.ocr || {}
  const validation = result.validation || []

  const validatorExternalContext = validation
    .flatMap((item) => item.warnings || [])
    .filter((warning) => typeof warning === "string" && warning.startsWith("External RAG context:"))
    .map((warning) => warning.replace("External RAG context:", "").trim())
    .join("\n\n")

  const materialCost = pricing.item_costs?.reduce((s, i) => s + (i.material_cost || 0), 0) || 0
  const logisticsCost = pricing.item_costs?.reduce((s, i) => s + (i.logistics_cost || 0), 0) || 0
  const marginTotal = pricing.item_costs?.reduce((s, i) => s + (i.margin_amount || 0), 0) || 0
  const gstAmount = gst.total_gst || 0
  const grandTotal = (pricing.total_subtotal || 0) + gstAmount

  const tabs = [
    { key: "overview", label: "Overview" },
    { key: "extraction", label: "Extracted Data" },
    { key: "costs", label: "Cost Breakdown" },
    { key: "agents", label: "Agent Logs" },
    { key: "rag", label: "RAG Evidence" },
  ]

  return (
    <div className="space-y-6 animate-fade-in max-w-[1400px] mx-auto">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 border border-surface-border rounded-btn hover:bg-surface-panel transition-colors text-surface-muted"><ArrowLeft size={16} /></Link>
          <div>
            <h1 className="text-xl font-semibold text-surface-text">RFQ Detail</h1>
            <p className="text-sm font-mono text-surface-muted mt-0.5">{rfqId}</p>
          </div>
        </div>
        <div className="flex gap-3">
          {rfq.status === "quoted" && (
            <a href={`${API_BASE}/rfq/${rfqId}/quote`} target="_blank" rel="noopener noreferrer" className="btn-primary flex items-center gap-2">
              <Download size={16} /> Download PDF
            </a>
          )}
          {rfq.sender_contact && <button className="btn-secondary flex items-center gap-2"><Send size={16} /> Contact Supplier</button>}
        </div>
      </div>

      {/* Pipeline Stepper */}
      <div className="panel p-4">
        <StatusStepper currentStatus={rfq.status} />
      </div>

      {/* Error display */}
      {rfq.error && (
        <div className="panel p-4 border-l-4 border-l-rose-500">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-rose-600 flex-shrink-0" size={18} />
            <p className="text-rose-800 text-sm font-medium">{rfq.error}</p>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left Column - Tabs & Content */}
        <div className="flex-1 space-y-6">
          {/* Tabs */}
          <div className="flex gap-1 p-1 bg-surface-panel rounded-lg border border-surface-border">
            {tabs.map(tab => (
              <button key={tab.key} onClick={() => setActiveTab(tab.key)}
                className={`flex-1 py-2 px-3 rounded-md text-sm font-medium transition-colors duration-150
                  ${activeTab === tab.key ? "bg-surface shadow-subtle text-primary border border-surface-border" : "text-surface-muted hover:text-surface-text hover:bg-surface/50 border border-transparent"}`}>
                {tab.label}
              </button>
            ))}
          </div>

          {/* Tab Content */}
          <div className="animate-fade-in">
            {activeTab === "overview" && (
              <div className="panel p-6 space-y-4">
                <h3 className="text-base font-semibold text-surface-text mb-4">Metadata</h3>
                {[
                  ["Status", <span className={`badge badge-${rfq.status}`}>{rfq.status}</span>],
                  ["Source", rfq.source_channel || "api"],
                  ["File Type", rfq.file_type || "text"],
                  ["Sender", rfq.sender_contact || "N/A"],
                  ["Created", rfq.created_at ? new Date(rfq.created_at).toLocaleString() : "—"],
                  ["Updated", rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "—"],
                  ["Pipeline Time", result.total_pipeline_ms ? `${result.total_pipeline_ms}ms` : "—"],
                ].map(([k, v], i) => (
                  <div key={i} className="flex justify-between py-2 border-b border-surface-border last:border-0">
                    <span className="text-surface-muted text-sm">{k}</span>
                    <span className="text-surface-text text-sm font-medium capitalize">{v}</span>
                  </div>
                ))}
              </div>
            )}

            {activeTab === "extraction" && (
              <div className="panel p-0 overflow-hidden">
                <div className="p-5 border-b border-surface-border bg-surface-50 flex items-center justify-between">
                  <h3 className="text-base font-semibold text-surface-text">Line Items</h3>
                  {ner.overall_confidence > 0 && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-surface-muted uppercase tracking-wider font-semibold">Confidence</span>
                      <span className="text-sm font-mono text-emerald-600 font-semibold">{((ner.overall_confidence || 0) * 100).toFixed(0)}%</span>
                    </div>
                  )}
                </div>
                {ner.line_items?.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead className="bg-surface-panel/50 border-b border-surface-border">
                        <tr>
                          {["Material", "Grade", "IS Code", "Dimensions", "Quantity", "Pincode"].map(h => (
                            <th key={h} className="text-left px-5 py-3 text-xs text-surface-muted font-medium uppercase">{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-surface-border">
                        {ner.line_items.map((item, i) => (
                          <tr key={i} className="hover:bg-surface-panel/30 transition-colors h-12">
                            <td className="px-5 text-surface-text font-medium">{item.material_type}</td>
                            <td className="px-5 text-surface-muted">{item.grade}</td>
                            <td className="px-5 text-surface-muted">{item.is_code || "—"}</td>
                            <td className="px-5 text-surface-muted font-mono text-xs">
                              {item.dimensions ? Object.entries(item.dimensions).map(([k,v]) => `${k}:${v}`).join(", ") : "—"}
                            </td>
                            <td className="px-5 text-surface-text font-medium">{item.quantity ? `${item.quantity.value} ${item.quantity.unit}` : "—"}</td>
                            <td className="px-5 text-surface-muted">{item.destination_pincode || "—"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : <div className="p-8 text-center text-surface-muted">No entities extracted yet.</div>}
              </div>
            )}

            {activeTab === "costs" && (
              <div className="space-y-4">
                {pricing.item_costs?.map((cost, i) => (
                  <div key={i} className="card p-5">
                    <h4 className="text-xs font-bold text-surface-muted uppercase tracking-wider mb-4 border-b border-surface-border pb-2">Line Item {i + 1}</h4>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {[
                        ["Material", cost.material_cost],
                        ["Logistics", cost.logistics_cost],
                        ["Margin", cost.margin_amount],
                        ["Subtotal", cost.subtotal],
                      ].map(([l, v]) => (
                        <div key={l}>
                          <p className="text-xs text-surface-muted mb-1">{l}</p>
                          <p className="text-base font-semibold text-surface-text">₹{(v || 0).toLocaleString("en-IN")}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )) || <div className="panel p-8 text-center text-surface-muted">Cost data not yet available.</div>}
              </div>
            )}

            {activeTab === "agents" && (
              <div className="panel p-6 space-y-5">
                <h3 className="text-base font-semibold text-surface-text border-b border-surface-border pb-3">Execution Timeline</h3>
                {Object.keys(timings).length > 0 ? (
                  <div className="space-y-4 pt-2">
                    {Object.entries(timings).map(([agent, ms]) => (
                      <div key={agent} className="flex items-center gap-4">
                        <div className="w-28 text-xs font-semibold text-surface-muted uppercase tracking-wider">{agent}</div>
                        <div className="flex-1 h-3 bg-surface-panel rounded-full overflow-hidden relative border border-surface-border">
                          <div className="h-full bg-primary transition-all duration-500 rounded-full"
                            style={{ width: `${Math.min(100, Math.max(1, (ms / Math.max(...Object.values(timings))) * 100))}%` }}>
                          </div>
                        </div>
                        <div className="w-20 text-right font-mono text-sm text-surface-text">
                          {ms}ms
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <p className="text-surface-muted text-center py-4">Agent logs not yet available.</p>}
              </div>
            )}

            {activeTab === "rag" && (
              <div className="panel p-6 space-y-4">
                <h3 className="text-base font-semibold text-surface-text border-b border-surface-border pb-3">External RAG Context</h3>
                {[
                  { label: "OCR", value: ocr.raw_text },
                  { label: "NER", value: ner.external_context },
                  { label: "Validator", value: validatorExternalContext },
                  { label: "Pricing", value: pricing.external_context },
                  { label: "GST", value: gst.external_context },
                ].map((item) => (
                  <div key={item.label} className="border border-surface-border rounded-lg p-4 bg-surface-50">
                    <div className="text-xs font-semibold text-surface-muted uppercase tracking-wider mb-2">{item.label}</div>
                    <div className="text-sm text-surface-text whitespace-pre-wrap">
                      {item.value || "No external context captured."}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Sticky Quote Summary */}
        <div className="w-full lg:w-80 flex-shrink-0">
          <div className="sticky top-24 panel p-6">
            <h3 className="text-base font-semibold text-surface-text mb-4 pb-3 border-b border-surface-border">Quote Summary</h3>
            {pricing.total_subtotal > 0 ? (
              <div className="space-y-1">
                <CostRow label="Material Cost" value={materialCost} />
                <CostRow label="Logistics" value={logisticsCost} />
                <CostRow label={`Margin (${pricing.margin_percent || 5}%)`} value={marginTotal} />
                <CostRow label={`GST (${gst.gst_rate_pct || 18}%)`} value={gstAmount} />
                <CostRow label="Grand Total" value={grandTotal} highlight />
              </div>
            ) : (
              <p className="text-surface-muted text-sm text-center py-4">Quote details pending.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default RFQDetail
