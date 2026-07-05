import React, { useState, useRef, useEffect } from 'react'
import { MessageSquare, X, Send, Loader, Bot, Sparkles } from 'lucide-react'
import useStore from '../store/workflowStore'

function Message({ msg }) {
  const isUser = msg.role === 'user'
  return (
    <div className={`flex gap-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      <div className={`w-6 h-6 rounded-full flex-shrink-0 flex items-center justify-center text-xs ${
        isUser ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-300'
      }`}>
        {isUser ? '👤' : <Bot size={12} />}
      </div>
      <div
        className={`max-w-[85%] px-3 py-2 rounded-xl text-xs leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-tr-sm'
            : 'bg-slate-800 text-slate-200 border border-slate-700 rounded-tl-sm'
        }`}
      >
        {msg.content}
      </div>
    </div>
  )
}

const SUGGESTED_PROMPTS = [
  'How can I improve this workflow?',
  'Explain the human review step',
  'What tools should I add?',
  'Summarize the current workflow',
]

export default function AIAssistant() {
  const { isAIOpen, toggleAI, aiMessages, isAILoading, sendAIMessage } = useStore()
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    if (isAIOpen) {
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: 'smooth' }), 100)
    }
  }, [aiMessages, isAIOpen])

  const submit = (msg) => {
    const text = (msg || input).trim()
    if (!text || isAILoading) return
    setInput('')
    sendAIMessage(text)
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <>
      {/* Floating button */}
      <button
        onClick={toggleAI}
        className={`fixed bottom-6 right-6 z-50 w-12 h-12 rounded-full shadow-xl flex items-center justify-center transition-all ${
          isAIOpen ? 'bg-slate-700 text-slate-300' : 'bg-indigo-600 hover:bg-indigo-500 text-white'
        }`}
        title="AI Assistant"
      >
        {isAIOpen ? <X size={18} /> : <Sparkles size={18} />}
      </button>

      {/* Chat panel */}
      {isAIOpen && (
        <div className="fixed bottom-20 right-6 z-50 w-80 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          style={{ height: '480px' }}>
          {/* Header */}
          <div className="flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-indigo-900/60 to-slate-900 border-b border-slate-700">
            <div className="w-7 h-7 rounded-full bg-indigo-600 flex items-center justify-center">
              <Bot size={14} className="text-white" />
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-100">WorkflowAI</p>
              <p className="text-[10px] text-slate-400">Powered by Groq / Llama 3.3</p>
            </div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-3">
            {aiMessages.length === 0 ? (
              <div className="space-y-3">
                <div className="flex gap-2">
                  <div className="w-6 h-6 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center">
                    <Bot size={12} className="text-slate-300" />
                  </div>
                  <div className="max-w-[85%] px-3 py-2 rounded-xl rounded-tl-sm text-xs leading-relaxed bg-slate-800 text-slate-200 border border-slate-700">
                    Hi! I'm WorkflowAI. I can help you design workflows, configure agents, and interpret results. What would you like to know?
                  </div>
                </div>
                <div className="pt-1">
                  <p className="text-[10px] text-slate-500 mb-2">Try asking:</p>
                  <div className="space-y-1">
                    {SUGGESTED_PROMPTS.map((p) => (
                      <button
                        key={p}
                        onClick={() => submit(p)}
                        className="w-full text-left text-[11px] text-indigo-300 bg-indigo-900/20 hover:bg-indigo-900/40 border border-indigo-800/40 rounded-lg px-3 py-1.5 transition-colors"
                      >
                        {p}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              aiMessages.map((msg, i) => <Message key={i} msg={msg} />)
            )}

            {isAILoading && (
              <div className="flex gap-2">
                <div className="w-6 h-6 rounded-full bg-slate-700 flex-shrink-0 flex items-center justify-center">
                  <Bot size={12} className="text-slate-300" />
                </div>
                <div className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-xl rounded-tl-sm">
                  <div className="flex gap-1 items-center">
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <div className="p-3 border-t border-slate-700">
            <div className="flex gap-2 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="Ask about your workflow…"
                rows={1}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-3 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none transition-colors"
                style={{ maxHeight: '80px', overflowY: 'auto' }}
              />
              <button
                onClick={() => submit()}
                disabled={!input.trim() || isAILoading}
                className="w-8 h-8 flex-shrink-0 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-xl flex items-center justify-center transition-colors"
              >
                {isAILoading ? <Loader size={13} className="animate-spin" /> : <Send size={13} />}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
