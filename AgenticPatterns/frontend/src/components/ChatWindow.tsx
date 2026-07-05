import { useEffect, useRef } from 'react'
import type { ChatMessage } from '../types'
import ResultRenderer from './ResultRenderer'
import './ChatWindow.css'

interface Props {
  messages: ChatMessage[]
}

function formatInputSummary(content: string): string {
  // content is JSON string of inputs — show a human-readable version
  try {
    const obj = JSON.parse(content) as Record<string, unknown>
    return Object.entries(obj)
      .map(([k, v]) => {
        const label = k.replace(/_/g, ' ')
        const val = typeof v === 'string' ? v : JSON.stringify(v)
        const preview = val.length > 80 ? val.slice(0, 80) + '…' : val
        return `${label}: ${preview}`
      })
      .join('\n')
  } catch {
    return content
  }
}

export default function ChatWindow({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (messages.length === 0) {
    return (
      <div className="chat-empty">
        <div className="chat-empty-icon">◈</div>
        <h2 className="chat-empty-title">Choose a pattern to get started</h2>
        <p className="chat-empty-sub">
          Select one of the 21 agentic patterns from the sidebar, fill in the inputs, and run it
          to see the AI response here.
        </p>
      </div>
    )
  }

  return (
    <div className="chat-window">
      {messages.map((msg) => (
        <div key={msg.id} className={`chat-message chat-message--${msg.role}`}>
          {msg.role === 'user' && (
            <div className="chat-bubble chat-bubble--user">
              <div className="chat-bubble-label">You · {msg.patternName}</div>
              <pre className="chat-bubble-text">{formatInputSummary(msg.content)}</pre>
            </div>
          )}

          {msg.role === 'assistant' && msg.isLoading && (
            <div className="chat-bubble chat-bubble--assistant">
              <div className="chat-bubble-label">
                <span className="spinner spinner--sm" />
                Running {msg.patternName}…
              </div>
              <div className="chat-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          {msg.role === 'assistant' && !msg.isLoading && msg.result && (
            <div className="chat-bubble chat-bubble--assistant">
              <div className="chat-bubble-label">{msg.patternName}</div>
              <ResultRenderer patternId={msg.patternId!} result={msg.result} />
            </div>
          )}

          {msg.role === 'error' && (
            <div className="chat-bubble chat-bubble--error">
              <div className="chat-bubble-label">Error</div>
              <p className="chat-bubble-text">{msg.content}</p>
            </div>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
