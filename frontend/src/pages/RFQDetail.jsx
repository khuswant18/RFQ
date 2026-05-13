import React, { useState, useEffect } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Download, Send, Clock, CheckCircle2, XCircle, Loader2, FileText, Cpu, DollarSign, Receipt, ChevronRight, AlertTriangle, Timer } from "lucide-react"

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1"

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
            <div className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-all duration-500
              ${done ? "bg-emerald-500/10 text-emerald-400" : active ? "bg-primary-500/10 text-primary-400" : "text-surface-600"}`}>
              <StepIcon size={14} className={active ? "animate-spin" : ""} />
              <span className="text-xs font-medium hidden lg:inline">{step.label}</span>
            </div>
            {i < PIPELINE_STEPS.length - 1 && (
              <ChevronRight size={14} className={done ? "text-emerald-500" : "text-surface-700"} />
            )}
          </React.Fragment>
        )
      })}
      {isFailed && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-rose-500/10 text-rose-400 ml-2">
          {currentStatus === "failed" ? <XCircle size={14} /> : <AlertTriangle size={14} />}
          <span className="text-xs font-medium">{currentStatus === "failed" ? "Failed" : "Review"}</span>
        </div>
      )}
    </div>
  )
}

function CostRow({ label, value, highlight }) {
  return (
    <div className={`flex justify-between py-2.5 ${highlight ? "border-t border-surface-700 mt-2 pt-4" : ""}`}>
      <span className={highlight ? "text-surface-200 font-semibold" : "text-surface-400"}>{label}</span>
      <span className={highlight ? "text-2xl font-bold text-gradient" : "text-surface-200 font-medium"}>
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

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 text-primary-500 animate-spin" /></div>
  if (error) return (
    <div className="glass-card p-8 text-center">
      <XCircle className="w-12 h-12 text-rose-400 mx-auto mb-4" />
      <p className="text-rose-400 text-lg">{error}</p>
      <Link to="/" className="btn-secondary mt-4 inline-block">← Back to Dashboard</Link>
    </div>
  )
  if (!rfq) return null

  const result = rfq.result || {}
  const pricing = result.pricing || {}
  const gst = result.gst || {}
  const quote = result.quote || {}
  const timings = result.agent_timings || {}
  const ner = result.ner || {}

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
  ]

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link to="/" className="p-2 rounded-lg hover:bg-surface-800 transition-colors"><ArrowLeft size={20} className="text-surface-400" /></Link>
          <div>
            <h1 className="text-2xl font-bold">RFQ Detail</h1>
            <p className="text-sm font-mono text-surface-500 mt-0.5">{rfqId}</p>
          </div>
        </div>
        <div className="flex gap-3">
          {rfq.status === "quoted" && (
            <a href={`${API_BASE}/rfq/${rfqId}/quote`} target="_blank" rel="noopener noreferrer" className="btn-primary flex items-center gap-2">
              <Download size={16} /> Download PDF
            </a>
          )}
          {rfq.sender_contact && <button className="btn-accent flex items-center gap-2"><Send size={16} /> Send WhatsApp</button>}
        </div>
      </div>

      {/* Pipeline Stepper */}
      <div className="glass-card p-4">
        <StatusStepper currentStatus={rfq.status} />
      </div>

      {/* Error display */}
      {rfq.error && (
        <div className="glass-card p-4 border-rose-500/30">
          <div className="flex items-center gap-3">
            <AlertTriangle className="text-rose-400 flex-shrink-0" size={20} />
            <p className="text-rose-400 text-sm">{rfq.error}</p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-1 bg-surface-900/50 rounded-xl border border-surface-800/50">
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-2.5 rounded-lg text-sm font-medium transition-all duration-300
              ${activeTab === tab.key ? "bg-primary-600/20 text-primary-400 border border-primary-500/30" : "text-surface-500 hover:text-surface-300"}`}>
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="animate-fade-in">
        {activeTab === "overview" && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass-card p-6 space-y-4">
              <h3 className="text-lg font-semibold mb-4">RFQ Information</h3>
              {[
                ["Status", <span className={`badge badge-${rfq.status}`}>{rfq.status}</span>],
                ["Source", rfq.source_channel || "api"],
                ["File Type", rfq.file_type || "text"],
                ["Sender", rfq.sender_contact || "N/A"],
                ["Created", rfq.created_at ? new Date(rfq.created_at).toLocaleString() : "—"],
                ["Updated", rfq.updated_at ? new Date(rfq.updated_at).toLocaleString() : "—"],
                ["Pipeline Time", result.total_pipeline_ms ? `${result.total_pipeline_ms}ms` : "—"],
              ].map(([k, v], i) => (
                <div key={i} className="flex justify-between py-1.5 border-b border-surface-800/30 last:border-0">
                  <span className="text-surface-500 text-sm">{k}</span>
                  <span className="text-surface-200 text-sm">{v}</span>
                </div>
              ))}
            </div>
            {pricing.total_subtotal > 0 && (
              <div className="glass-card p-6">
                <h3 className="text-lg font-semibold mb-4">Quote Summary</h3>
                <CostRow label="Material Cost" value={materialCost} />
                <CostRow label="Logistics & Loading" value={logisticsCost} />
                <CostRow label={`Margin (${pricing.margin_percent || 5}%)`} value={marginTotal} />
                <CostRow label={`GST (${gst.gst_rate_pct || 18}% ${gst.tax_type || ""})`} value={gstAmount} />
                <CostRow label="Grand Total" value={grandTotal} highlight />
              </div>
            )}
          </div>
        )}

        {activeTab === "extraction" && (
          <div className="glass-card p-6">
            <h3 className="text-lg font-semibold mb-4">Extracted Entities</h3>
            {ner.line_items?.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead><tr className="border-b border-surface-800">
                    {["Material", "Grade", "IS Code", "Dimensions", "Quantity", "Pincode"].map(h => (
                      <th key={h} className="text-left px-4 py-2 text-xs text-surface-500 uppercase">{h}</th>
                    ))}
                  </tr></thead>
                  <tbody>
                    {ner.line_items.map((item, i) => (
                      <tr key={i} className="border-b border-surface-800/30">
                        <td className="px-4 py-3 text-surface-200">{item.material_type}</td>
                        <td className="px-4 py-3 text-surface-200">{item.grade}</td>
                        <td className="px-4 py-3 text-surface-400">{item.is_code || "—"}</td>
                        <td className="px-4 py-3 text-surface-400 font-mono text-xs">
                          {item.dimensions ? Object.entries(item.dimensions).map(([k,v]) => `${k}:${v}`).join(", ") : "—"}
                        </td>
                        <td className="px-4 py-3 text-surface-200">{item.quantity ? `${item.quantity.value} ${item.quantity.unit}` : "—"}</td>
                        <td className="px-4 py-3 text-surface-400">{item.destination_pincode || "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : <p className="text-surface-500">No entities extracted yet.</p>}
            {ner.overall_confidence > 0 && (
              <div className="mt-4 pt-4 border-t border-surface-800/50 flex items-center gap-4">
                <span className="text-sm text-surface-500">Confidence:</span>
                <div className="flex-1 h-2 bg-surface-800 rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-primary-500 to-accent-500 rounded-full transition-all duration-1000"
                    style={{ width: `${(ner.overall_confidence || 0) * 100}%` }} />
                </div>
                <span className="text-sm font-mono text-primary-400">{((ner.overall_confidence || 0) * 100).toFixed(0)}%</span>
              </div>
            )}
          </div>
        )}

        {activeTab === "costs" && (
          <div className="space-y-4">
            {pricing.item_costs?.map((cost, i) => (
              <div key={i} className="glass-card p-5">
                <h4 className="text-sm font-semibold text-surface-400 mb-3">Item {i + 1}</h4>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  {[
                    ["Material", cost.material_cost],
                    ["Logistics", cost.logistics_cost],
                    ["Margin", cost.margin_amount],
                    ["Subtotal", cost.subtotal],
                  ].map(([l, v]) => (
                    <div key={l}>
                      <p className="text-xs text-surface-500">{l}</p>
                      <p className="text-lg font-semibold text-surface-200">₹{(v || 0).toLocaleString("en-IN")}</p>
                    </div>
                  ))}
                </div>
              </div>
            )) || <p className="text-surface-500 glass-card p-6">Cost data not yet available.</p>}
          </div>
        )}

        {activeTab === "agents" && (
          <div className="glass-card p-6 space-y-4">
            <h3 className="text-lg font-semibold mb-4">Agent Execution Timeline</h3>
            {Object.keys(timings).length > 0 ? (
              <div className="space-y-3">
                {Object.entries(timings).map(([agent, ms], i) => (
                  <div key={agent} className="flex items-center gap-4 animate-slide-up" style={{ animationDelay: `${i * 100}ms` }}>
                    <div className="w-28 text-sm font-medium text-surface-300 capitalize">{agent}</div>
                    <div className="flex-1 h-6 bg-surface-800 rounded-lg overflow-hidden relative">
                      <div className="h-full bg-gradient-to-r from-primary-600 to-accent-500 rounded-lg transition-all duration-1000 flex items-center px-2"
                        style={{ width: `${Math.min(100, (ms / Math.max(...Object.values(timings))) * 100)}%` }}>
                        <span className="text-[10px] font-mono text-white/80">{ms}ms</span>
                      </div>
                    </div>
                    <div className="w-16 text-right">
                      <Timer size={12} className="inline text-surface-500" /> <span className="text-xs text-surface-400">{ms}ms</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : <p className="text-surface-500">Agent logs not yet available.</p>}
          </div>
        )}
      </div>
    </div>
  )
}

export default RFQDetail
