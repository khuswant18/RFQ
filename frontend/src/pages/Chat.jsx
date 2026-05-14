import React from 'react'
import { Send, Sparkles } from 'lucide-react'

const quickPrompts = [
  'Extract items from: 12mm Fe500 10 ton Sachin GIDC',
  'Estimate GST for TMT bars to Mumbai',
  'Explain quote validity and margin',
  'Validate grade Fe500 for TMT',
]

const seedMessages = [
  {
    id: 'm1',
    role: 'assistant',
    text: 'Welcome to SRIP Chat Simulator. Ask about an RFQ and I will respond with a simulated extraction or pricing hint.',
    time: 'Now',
  },
  {
    id: 'm2',
    role: 'assistant',
    text: 'Try: "12mm sariya Fe500 10 ton Sachin GIDC" or "GST for Rajkot delivery".',
    time: 'Now',
  },
]

function simulateReply(input) {
  const lower = input.toLowerCase()
  if (lower.includes('gst')) {
    return 'GST rule: Gujarat pincodes apply CGST+SGST at 18%. Non-Gujarat uses IGST at 18%.'
  }
  if (lower.includes('price') || lower.includes('mcx')) {
    return 'Pricing: I would fetch MCX rate, add logistics, and margin to compute subtotal and GST.'
  }
  if (lower.includes('validate') || lower.includes('grade')) {
    return 'Validation: Fe500 is valid for TMT bars (IS 1786). I will flag impossible grade-material pairs.'
  }
  if (lower.includes('extract') || lower.includes('sariya') || lower.includes('tmt')) {
    return 'Extraction: material=TMT_Bar, grade=Fe500, diameter=12mm, quantity=10 tons, location=Sachin GIDC.'
  }
  return 'Got it. I will parse the RFQ, validate grades, calculate pricing and GST, then prepare a quote.'
}

function ChatMessage({ role, text, time }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className={`chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}>
        <p className="text-sm leading-relaxed">{text}</p>
        <span className="text-[10px] text-surface-500 mt-2 block">{time}</span>
      </div>
    </div>
  )
}

export default function ChatPage() {
  const [messages, setMessages] = React.useState(seedMessages)
  const [input, setInput] = React.useState('')
  const [isTyping, setIsTyping] = React.useState(false)

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed) return

    const userMessage = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
      time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setIsTyping(true)

    setTimeout(() => {
      const reply = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        text: simulateReply(trimmed),
        time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      }
      setMessages(prev => [...prev, reply])
      setIsTyping(false)
    }, 700)
  }

  return (
    <div className="animate-fade-in">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Chat Simulator</h1>
          <p className="text-surface-500">Simulate SRIP extraction and pricing responses without running the pipeline.</p>
        </div>
        <div className="badge badge-quoted">
          <Sparkles size={14} />
          Simulated
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_280px] gap-6">
        <div className="glass-card p-6 flex flex-col h-[70vh]">
          <div className="flex-1 overflow-y-auto pr-2 space-y-4">
            {messages.map(msg => (
              <ChatMessage key={msg.id} role={msg.role} text={msg.text} time={msg.time} />
            ))}
            {isTyping && (
              <div className="flex justify-start">
                <div className="chat-bubble chat-bubble-assistant">
                  <p className="text-sm text-surface-400 loading-dots">Typing</p>
                </div>
              </div>
            )}
          </div>

          <div className="mt-6 flex items-center gap-3">
            <input
              className="input-field"
              placeholder="Ask about an RFQ, pricing, or GST..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
            />
            <button className="btn-primary" onClick={handleSend}>
              <Send size={16} />
            </button>
          </div>
        </div>

        <div className="glass-card p-5 space-y-4 h-fit">
          <h2 className="text-sm font-semibold text-surface-300 uppercase tracking-widest">Quick Prompts</h2>
          <div className="space-y-3">
            {quickPrompts.map(prompt => (
              <button
                key={prompt}
                className="w-full text-left px-4 py-3 rounded-xl border border-surface-700 bg-surface-900/40 text-sm text-surface-200 hover:border-primary-500/40 hover:text-surface-50 transition-all"
                onClick={() => setInput(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
          <div className="text-xs text-surface-500 pt-2">
            This is a local simulation to demo the agent behavior.
          </div>
        </div>
      </div>
    </div>
  )
}
