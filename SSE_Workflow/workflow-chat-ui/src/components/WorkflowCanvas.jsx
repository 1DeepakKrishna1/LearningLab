import { useEffect } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  MarkerType,
  Position,
  Handle,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

// ── Node colour by type ──────────────────────────────────────────────────────
const TYPE_COLOR = {
  start:            { bg: '#1e3a2f', border: '#34d399', icon: '▶', accent: '#34d399' },
  end:              { bg: '#1e2a3a', border: '#60a5fa', icon: '■', accent: '#60a5fa' },
  automatic:        { bg: '#1e2233', border: '#6c8ef5', icon: '⚙', accent: '#6c8ef5' },
  human_in_the_loop:{ bg: '#2e2010', border: '#fbbf24', icon: '👤', accent: '#fbbf24' },
  prompt_agent:     { bg: '#1e1e33', border: '#a78bfa', icon: '✦', accent: '#a78bfa' },
  react_agent:      { bg: '#1e2030', border: '#818cf8', icon: '⟳', accent: '#818cf8' },
  reflection_agent: { bg: '#1e2830', border: '#38bdf8', icon: '◈', accent: '#38bdf8' },
  guardrails:       { bg: '#2a1e1e', border: '#f87171', icon: '🛡', accent: '#f87171' },
  supervisor:       { bg: '#2a1e28', border: '#e879f9', icon: '◉', accent: '#e879f9' },
  orchestrator:     { bg: '#1e2820', border: '#4ade80', icon: '◎', accent: '#4ade80' },
  conditional:      { bg: '#2a2010', border: '#fb923c', icon: '◆', accent: '#fb923c' },
  tool:             { bg: '#1a1d27', border: '#475569', icon: '🔧', accent: '#475569' },
}
const DEFAULT_COLOR = { bg: '#1a1d27', border: '#2e3348', icon: '○', accent: '#6c8ef5' }

// ── Execution state overlays ─────────────────────────────────────────────────
const STATE_STYLE = {
  running:        { border: '#6c8ef5', glow: '0 0 12px rgba(108,142,245,0.5)', cls: 'node-running' },
  awaiting_input: { border: '#fbbf24', glow: '0 0 12px rgba(251,191,36,0.5)',  cls: 'node-awaiting' },
  paused:         { border: '#fb923c', glow: '0 0 8px rgba(251,146,60,0.4)',   cls: '' },
  completed:      { border: '#34d399', glow: '0 0 8px rgba(52,211,153,0.25)',  cls: '' },
  failed:         { border: '#f87171', glow: '0 0 8px rgba(248,113,113,0.4)',  cls: '' },
}

function WorkflowNode({ data }) {
  const nodeType = data.node_kind === 'tool' ? 'tool' : (data.type || 'automatic')
  const colors = TYPE_COLOR[nodeType] || DEFAULT_COLOR
  const execState = data.execState
  const stateStyle = STATE_STYLE[execState] || null

  const border = stateStyle ? stateStyle.border : colors.border
  const glow   = stateStyle ? stateStyle.glow   : 'none'
  const cls    = stateStyle ? stateStyle.cls     : ''

  const statusBadge = {
    running:        { label: 'Running',    color: '#6c8ef5' },
    awaiting_input: { label: 'Input Needed', color: '#fbbf24' },
    paused:         { label: 'Paused',     color: '#fb923c' },
    completed:      { label: 'Done',       color: '#34d399' },
    failed:         { label: 'Failed',     color: '#f87171' },
  }[execState]

  const handleStyle = {
    width: 10,
    height: 10,
    background: border,
    border: '2px solid var(--bg)',
    borderRadius: '50%',
  }

  return (
    <div
      className={cls}
      style={{
        background: colors.bg,
        border: `2px solid ${border}`,
        borderRadius: 10,
        padding: '10px 14px',
        minWidth: 160,
        maxWidth: 200,
        boxShadow: glow,
        transition: 'border-color 0.3s, box-shadow 0.3s',
        fontFamily: "'Inter', sans-serif",
        position: 'relative',
      }}
    >
      {/* Connection handles — required by ReactFlow for edges to render */}
      <Handle
        type="target"
        position={Position.Left}
        style={handleStyle}
      />
      <Handle
        type="source"
        position={Position.Right}
        style={handleStyle}
      />

      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, marginBottom: 4 }}>
        <span style={{
          fontSize: 16,
          lineHeight: 1,
          flexShrink: 0,
          color: colors.accent,
          marginTop: 1,
        }}>
          {colors.icon}
        </span>
        <div style={{ minWidth: 0 }}>
          <div style={{
            fontSize: 12,
            fontWeight: 600,
            color: '#e2e8f0',
            lineHeight: 1.3,
            wordBreak: 'break-word',
          }}>
            {data.label}
          </div>
          <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>
            {nodeType.replace(/_/g, ' ')}
          </div>
        </div>
      </div>

      {statusBadge && (
        <div style={{
          marginTop: 6,
          fontSize: 10,
          fontWeight: 600,
          color: statusBadge.color,
          background: `${statusBadge.color}22`,
          border: `1px solid ${statusBadge.color}44`,
          borderRadius: 4,
          padding: '2px 6px',
          display: 'inline-block',
          letterSpacing: '0.04em',
          textTransform: 'uppercase',
        }}>
          {statusBadge.label}
        </div>
      )}

      {execState === 'completed' && (
        <div style={{
          position: 'absolute',
          top: 6,
          right: 8,
          fontSize: 12,
          color: '#34d399',
        }}>✓</div>
      )}
    </div>
  )
}

const nodeTypes = { workflowNode: WorkflowNode }

function buildFlowNodes(wfNodes, nodeStates) {
  return wfNodes.map(n => {
    const data = n.data || {}
    const isAgent = n.node_kind === 'agent'
    return {
      id: n.id,
      type: 'workflowNode',
      position: n.position,
      data: {
        label: data.name || n.id,
        type: data.type,
        node_kind: n.node_kind,
        agent_id: n.agent_id,
        tool_id: n.tool_id,
        execState: nodeStates[n.id] || null,
      },
    }
  })
}

function buildFlowEdges(wfEdges) {
  return wfEdges.map(e => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: e.label || '',
    type: 'smoothstep',
    animated: false,
    style: { stroke: '#2e3348', strokeWidth: 1.5 },
    labelStyle: { fill: '#64748b', fontSize: 10 },
    labelBgStyle: { fill: '#1a1d27' },
    markerEnd: { type: MarkerType.ArrowClosed, color: '#2e3348' },
  }))
}

export default function WorkflowCanvas({ workflow, nodeStates }) {
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])

  // Rebuild nodes when workflow or states change
  useEffect(() => {
    if (!workflow) { setNodes([]); setEdges([]); return }
    setNodes(buildFlowNodes(workflow.nodes, nodeStates))
    setEdges(buildFlowEdges(workflow.edges))
  }, [workflow, nodeStates])

  if (!workflow) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 12,
        color: 'var(--text3)',
        background: 'var(--bg)',
        fontFamily: "'Inter', sans-serif",
      }}>
        <div style={{ fontSize: 48, opacity: 0.3 }}>◎</div>
        <div style={{ fontSize: 14, fontWeight: 500 }}>No workflow loaded</div>
        <div style={{ fontSize: 12 }}>Select a workflow and click Run</div>
      </div>
    )
  }

  return (
    <div style={{ flex: 1, position: 'relative', background: 'var(--bg)' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e2233" gap={24} size={1} />
        <Controls showInteractive={false} />
        <MiniMap
          nodeColor={n => {
            const state = n.data?.execState
            if (state === 'completed')      return '#34d399'
            if (state === 'running')        return '#6c8ef5'
            if (state === 'awaiting_input') return '#fbbf24'
            if (state === 'failed')         return '#f87171'
            const t = n.data?.type
            return (TYPE_COLOR[t] || DEFAULT_COLOR).accent
          }}
          maskColor="rgba(15,17,23,0.7)"
        />
      </ReactFlow>

      {/* Legend */}
      <div style={{
        position: 'absolute',
        bottom: 12,
        left: 12,
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        padding: '8px 12px',
        display: 'flex',
        gap: 14,
        fontSize: 11,
        color: 'var(--text2)',
        fontFamily: "'Inter', sans-serif",
      }}>
        {[
          { color: '#6c8ef5', label: 'Running' },
          { color: '#fbbf24', label: 'Needs Input' },
          { color: '#fb923c', label: 'Paused' },
          { color: '#34d399', label: 'Done' },
        ].map(({ color, label }) => (
          <span key={label} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: color, flexShrink: 0 }} />
            {label}
          </span>
        ))}
      </div>
    </div>
  )
}
