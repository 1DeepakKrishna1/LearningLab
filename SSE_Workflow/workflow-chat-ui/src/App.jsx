import { useState, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar.jsx'
import WorkflowCanvas from './components/WorkflowCanvas.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import { useSSE } from './hooks/useSSE.js'
import { executeWorkflow, fetchWorkflow } from './api.js'

// ── Helpers ──────────────────────────────────────────────────────────────────

function ts() {
  return new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

let _msgId = 0
function mkMsg(type, title, body = null, extra = {}) {
  return { id: ++_msgId, type, title, body, time: ts(), ...extra }
}

// ── App ──────────────────────────────────────────────────────────────────────

export default function App() {
  const [workflow, setWorkflow]         = useState(null)   // full workflow definition
  const [executionId, setExecutionId]   = useState(null)
  const [executing, setExecuting]       = useState(false)
  const [messages, setMessages]         = useState([])
  // nodeStates: { [nodeId]: 'running' | 'awaiting_input' | 'paused' | 'completed' | 'failed' }
  const [nodeStates, setNodeStates]     = useState({})
  const lastNodeRef = useRef(null)

  // ── SSE event handler ──────────────────────────────────────────────────────

  const handleSSE = useCallback((event, data) => {
    switch (event) {
      case 'connected':
        addMsg(mkMsg('system', 'SSE stream connected', `Workflow: ${data.workflow_name} · Mode: ${data.mode}`))
        break

      case 'workflow_started':
        addMsg(mkMsg('system', `Workflow started: ${data.workflow_name}`,
          `${data.total_nodes} nodes to execute · Mode: ${data.mode}`))
        break

      case 'node_started':
        lastNodeRef.current = data.node_id
        setNodeState(data.node_id, 'running')
        addMsg(mkMsg('node_started',
          `Step ${data.step}/${data.total}: ${data.node_name}`,
          `Type: ${(data.node_type || '').replace(/_/g, ' ')} · Agent: ${data.agent_id || data.tool_id || '—'}`
        ))
        break

      case 'awaiting_input':
        setNodeState(data.node_id, 'awaiting_input')
        addMsg(mkMsg('awaiting_input',
          `Input needed: ${data.node_name}`,
          data.message,
          { event: data, submitted: false }
        ))
        break

      case 'node_completed':
        setNodeState(data.node_id, 'completed')
        addMsg(mkMsg('node_done',
          `Done: ${data.node_name}`,
          null,
          { detail: data.result }
        ))
        break

      case 'awaiting_resume':
        setNodeState(data.node_id, 'paused')
        addMsg(mkMsg('awaiting_resume',
          `Paused after step ${data.step}/${data.total}: ${data.node_name}`,
          `Next: ${data.next_node_name}`,
          { resumed: false }
        ))
        break

      case 'workflow_completed':
        setExecuting(false)
        addMsg(mkMsg('completed',
          `Workflow complete! ${data.total_nodes} nodes executed.`,
          data.message
        ))
        break

      case 'workflow_failed':
        setExecuting(false)
        addMsg(mkMsg('failed', 'Workflow failed', data.message))
        // Mark current node as failed
        if (lastNodeRef.current) setNodeState(lastNodeRef.current, 'failed')
        break

      case '_error':
        addMsg(mkMsg('error', 'Connection error', data.message))
        break

      default:
        break
    }
  }, [])

  // ── SSE hook ───────────────────────────────────────────────────────────────

  useSSE(executionId, handleSSE)

  // ── State helpers ──────────────────────────────────────────────────────────

  function addMsg(msg) {
    setMessages(prev => [...prev, msg])
  }

  function setNodeState(nodeId, state) {
    setNodeStates(prev => ({ ...prev, [nodeId]: state }))
  }

  // ── Select workflow (loads canvas immediately, no execution) ──────────────

  async function handleSelect(wfSummary) {
    // Reset any prior execution state so the canvas shows a clean workflow
    setMessages([])
    setNodeStates({})
    setExecutionId(null)
    lastNodeRef.current = null
    try {
      const fullWf = await fetchWorkflow(wfSummary.id)
      setWorkflow(fullWf)
      addMsg(mkMsg('system',
        `${wfSummary.name}`,
        `${fullWf.nodes.length} nodes · ${fullWf.edges.length} edges · ${wfSummary.tags?.join(', ') || 'no tags'}`
      ))
    } catch (e) {
      addMsg(mkMsg('error', 'Failed to load workflow', e.message))
    }
  }

  // ── Execute workflow ───────────────────────────────────────────────────────

  async function handleExecute(wfSummary, mode) {
    try {
      // Reset execution state (keep the already-loaded workflow on canvas)
      setMessages([])
      setNodeStates({})
      setExecutionId(null)
      lastNodeRef.current = null

      // Reload full definition in case it wasn't selected beforehand
      const fullWf = await fetchWorkflow(wfSummary.id)
      setWorkflow(fullWf)

      addMsg(mkMsg('system',
        `Starting: ${wfSummary.name}`,
        `Mode: ${mode} · ${fullWf.nodes.length} nodes, ${fullWf.edges.length} edges`
      ))

      setExecuting(true)

      const result = await executeWorkflow(wfSummary.id, mode)

      if (mode === 'FULL_NO_SSE') {
        // Do NOT set executionId — that would trigger the SSE hook which
        // would hit /events/ and get a 400, firing a spurious error message.
        addMsg(mkMsg('completed',
          'Workflow completed (no SSE)',
          `All nodes executed synchronously. GET /execution/${result.execution_id}/status for full results.`
        ))
        setExecuting(false)
      } else {
        // Only open the SSE stream for modes that support it
        setExecutionId(result.execution_id)
        addMsg(mkMsg('system', 'Connecting to SSE stream…',
          `execution_id: ${result.execution_id}`))
      }
    } catch (e) {
      setExecuting(false)
      addMsg(mkMsg('failed', 'Failed to start workflow', e.message))
    }
  }

  // ── Handle input submission (from ChatPanel/InputForm) ─────────────────────

  const handleInputSubmit = useCallback((msgId, nodeId, inputData) => {
    setMessages(prev => prev.map(m => {
      if (m.id !== msgId) return m
      if (m.type === 'awaiting_input') return { ...m, submitted: true }
      if (m.type === 'awaiting_resume') return { ...m, resumed: true }
      return m
    }))
    if (nodeId) setNodeState(nodeId, 'completed')
  }, [])

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <div style={{
      display: 'flex',
      height: '100vh',
      width: '100vw',
      overflow: 'hidden',
    }}>
      <Sidebar onExecute={handleExecute} onSelect={handleSelect} executing={executing} />

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
        {/* Top bar */}
        <div style={{
          height: 44,
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          padding: '0 16px',
          gap: 12,
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--text3)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
            Workflow Canvas
          </span>
          {workflow && (
            <>
              <span style={{ color: 'var(--border)' }}>|</span>
              <span style={{ fontSize: 12, color: 'var(--text2)', fontWeight: 500 }}>{workflow.name}</span>
              <span style={{ fontSize: 11, color: 'var(--text3)' }}>
                {workflow.nodes.length} nodes · {workflow.edges.length} edges
              </span>
            </>
          )}
          {executing && (
            <span style={{
              marginLeft: 'auto',
              fontSize: 11,
              color: 'var(--accent)',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}>
              <span style={{
                display: 'inline-block',
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: 'var(--accent)',
                animation: 'pulse-ring 1.5s ease-out infinite',
              }} />
              Executing
            </span>
          )}
        </div>

        {/* Canvas + Chat */}
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
          <WorkflowCanvas workflow={workflow} nodeStates={nodeStates} />
          <ChatPanel
            messages={messages}
            executionId={executionId}
            onInputSubmit={handleInputSubmit}
            workflow={workflow}
          />
        </div>
      </div>
    </div>
  )
}
