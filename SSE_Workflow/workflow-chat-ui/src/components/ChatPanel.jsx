import { useEffect, useRef } from 'react'
import InputForm from './InputForm.jsx'
import { provideInput, resumeExecution } from '../api.js'

// ── Message type definitions ─────────────────────────────────────────────────
// type: 'system' | 'node_started' | 'node_done' | 'awaiting_input' | 'awaiting_resume'
//       | 'input_submitted' | 'completed' | 'failed' | 'user_action' | 'error'

const TYPE_CONFIG = {
  system:          { icon: '◎', color: 'var(--text3)',  bg: 'transparent',     border: 'var(--border)' },
  node_started:    { icon: '▷', color: 'var(--accent)', bg: 'rgba(108,142,245,0.06)', border: 'rgba(108,142,245,0.2)' },
  node_done:       { icon: '✓', color: 'var(--green)',  bg: 'rgba(52,211,153,0.06)',  border: 'rgba(52,211,153,0.2)' },
  awaiting_input:  { icon: '⚠', color: 'var(--yellow)', bg: 'rgba(251,191,36,0.06)',  border: 'rgba(251,191,36,0.2)' },
  awaiting_resume: { icon: '⏸', color: 'var(--orange)', bg: 'rgba(251,146,60,0.06)',  border: 'rgba(251,146,60,0.2)' },
  input_submitted: { icon: '↵', color: 'var(--green)',  bg: 'rgba(52,211,153,0.04)',  border: 'rgba(52,211,153,0.1)' },
  completed:       { icon: '★', color: 'var(--green)',  bg: 'rgba(52,211,153,0.08)',  border: 'var(--green)' },
  failed:          { icon: '✗', color: 'var(--red)',    bg: 'rgba(248,113,113,0.08)', border: 'var(--red)' },
  user_action:     { icon: '→', color: 'var(--accent2)',bg: 'rgba(167,139,250,0.06)', border: 'rgba(167,139,250,0.2)' },
  error:           { icon: '!', color: 'var(--red)',    bg: 'rgba(248,113,113,0.06)', border: 'rgba(248,113,113,0.2)' },
}

function MessageBubble({ msg, executionId, onInputSubmit }) {
  const cfg = TYPE_CONFIG[msg.type] || TYPE_CONFIG.system

  return (
    <div style={{
      marginBottom: 8,
      padding: '10px 12px',
      borderRadius: 8,
      background: cfg.bg,
      border: `1px solid ${cfg.border}`,
      fontFamily: "'Inter', sans-serif",
    }}>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginBottom: 2 }}>
        <span style={{ fontSize: 13, color: cfg.color, flexShrink: 0 }}>{cfg.icon}</span>
        <span style={{ fontSize: 12, fontWeight: 600, color: cfg.color }}>{msg.title}</span>
        <span style={{ fontSize: 10, color: 'var(--text3)', marginLeft: 'auto', flexShrink: 0 }}>
          {msg.time}
        </span>
      </div>

      {msg.body && (
        <div style={{ fontSize: 12, color: 'var(--text2)', marginLeft: 21, lineHeight: 1.5 }}>
          {msg.body}
        </div>
      )}

      {msg.detail && (
        <pre style={{
          marginLeft: 21,
          marginTop: 6,
          padding: '6px 10px',
          background: 'var(--surface)',
          borderRadius: 6,
          fontSize: 11,
          color: 'var(--text2)',
          overflowX: 'auto',
          fontFamily: "'JetBrains Mono', monospace",
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {typeof msg.detail === 'string' ? msg.detail : JSON.stringify(msg.detail, null, 2)}
        </pre>
      )}

      {msg.type === 'awaiting_input' && msg.event && !msg.submitted && (
        <div style={{ marginLeft: 21, marginTop: 8 }}>
          <InputForm
            event={msg.event}
            onSubmit={async (nodeId, inputData) => {
              try {
                await provideInput(executionId, nodeId, inputData)
                onInputSubmit(msg.id, nodeId, inputData)
              } catch (e) {
                alert('Failed to submit input: ' + e.message)
              }
            }}
          />
        </div>
      )}

      {msg.type === 'awaiting_input' && msg.submitted && (
        <div style={{
          marginLeft: 21,
          marginTop: 6,
          fontSize: 11,
          color: 'var(--green)',
          display: 'flex',
          alignItems: 'center',
          gap: 6,
        }}>
          <span>✓</span> Input submitted — execution resumed
        </div>
      )}

      {msg.type === 'awaiting_resume' && !msg.resumed && executionId && (
        <div style={{ marginLeft: 21, marginTop: 8 }}>
          <button
            style={{
              padding: '6px 16px',
              borderRadius: 6,
              border: '1px solid var(--orange)',
              background: 'rgba(251,146,60,0.1)',
              color: 'var(--orange)',
              fontSize: 12,
              fontWeight: 600,
              cursor: 'pointer',
            }}
            onClick={async () => {
              try {
                await resumeExecution(executionId)
                onInputSubmit(msg.id, null, null)
              } catch (e) {
                alert('Resume failed: ' + e.message)
              }
            }}
          >
            ▶ Resume Next Step
          </button>
        </div>
      )}
    </div>
  )
}

export default function ChatPanel({ messages, executionId, onInputSubmit, workflow }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div style={{
      width: 380,
      minWidth: 340,
      display: 'flex',
      flexDirection: 'column',
      background: 'var(--surface)',
      borderLeft: '1px solid var(--border)',
    }}>
      {/* Header */}
      <div style={{
        padding: '14px 16px 12px',
        borderBottom: '1px solid var(--border)',
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        flexShrink: 0,
      }}>
        <div style={{
          width: 28,
          height: 28,
          borderRadius: 8,
          background: 'linear-gradient(135deg, var(--accent), var(--accent2))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: 14,
          flexShrink: 0,
        }}>✦</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)' }}>
            {workflow ? workflow.name : 'Workflow AI'}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text3)' }}>
            {executionId
              ? `ID: ${executionId.slice(0, 8)}…`
              : 'Ready to execute'}
          </div>
        </div>
        {executionId && (
          <div style={{
            marginLeft: 'auto',
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: 'var(--green)',
            boxShadow: '0 0 6px var(--green)',
            flexShrink: 0,
          }} />
        )}
      </div>

      {/* Messages */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '12px 12px 0',
      }}>
        {messages.length === 0 && (
          <div style={{
            textAlign: 'center',
            padding: '40px 16px',
            color: 'var(--text3)',
            fontSize: 13,
          }}>
            <div style={{ fontSize: 36, marginBottom: 12, opacity: 0.4 }}>✦</div>
            <div style={{ fontWeight: 500, marginBottom: 6 }}>Select a workflow to begin</div>
            <div style={{ fontSize: 11 }}>Execution events will appear here in real-time</div>
          </div>
        )}
        {messages.map(msg => (
          <MessageBubble
            key={msg.id}
            msg={msg}
            executionId={executionId}
            onInputSubmit={onInputSubmit}
          />
        ))}
        <div ref={bottomRef} style={{ height: 12 }} />
      </div>

      {/* Footer */}
      <div style={{
        padding: '10px 12px',
        borderTop: '1px solid var(--border)',
        fontSize: 11,
        color: 'var(--text3)',
        textAlign: 'center',
        flexShrink: 0,
      }}>
        {executionId
          ? 'Streaming live via SSE'
          : 'Workflow execution log'}
      </div>
    </div>
  )
}
