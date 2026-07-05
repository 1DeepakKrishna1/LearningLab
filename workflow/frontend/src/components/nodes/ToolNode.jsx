import React, { memo } from 'react'
import { Handle, Position } from 'reactflow'

const TOOL_TYPE_STYLES = {
  api_call:       { color: '#0ea5e9', badge: 'bg-sky-900/70 text-sky-300',       label: 'API' },
  data_transform: { color: '#14b8a6', badge: 'bg-teal-900/70 text-teal-300',     label: 'Transform' },
  notification:   { color: '#f59e0b', badge: 'bg-amber-900/70 text-amber-300',   label: 'Notify' },
  database:       { color: '#a855f7', badge: 'bg-purple-900/70 text-purple-300', label: 'Database' },
  file_io:        { color: '#f97316', badge: 'bg-orange-900/70 text-orange-300', label: 'File' },
  ai_inference:   { color: '#ec4899', badge: 'bg-pink-900/70 text-pink-300',     label: 'AI' },
  approval:       { color: '#f43f5e', badge: 'bg-rose-900/70 text-rose-300',     label: 'Approval' },
  webhook:        { color: '#06b6d4', badge: 'bg-cyan-900/70 text-cyan-300',     label: 'Webhook' },
}

const EXEC_STYLES = {
  pending:   { icon: '○', iconCls: 'text-slate-400' },
  running:   { icon: '▶', iconCls: 'text-blue-400 animate-pulse' },
  completed: { icon: '✓', iconCls: 'text-green-400' },
  failed:    { icon: '✗', iconCls: 'text-red-400' },
  skipped:   { icon: '⏭', iconCls: 'text-slate-500' },
}

const TOOL_ICONS = {
  api_call:       '🌐',
  data_transform: '⇌',
  notification:   '✉',
  database:       '🗄',
  file_io:        '📄',
  ai_inference:   '🧠',
  approval:       '🛡',
  webhook:        '⚡',
}

const ToolNode = memo(({ data, selected }) => {
  const ts = TOOL_TYPE_STYLES[data.toolType] || { color: '#0ea5e9', badge: 'bg-sky-900/70 text-sky-300', label: 'Tool' }
  const es = data.executionStatus ? EXEC_STYLES[data.executionStatus] : null
  const accentColor = ts.color

  return (
    <div className="relative w-44">
      {/* Target handle (top) */}
      <Handle type="target" position={Position.Top} className="!top-[-5px]" />

      {/* Parallelogram background */}
      <div
        className="absolute inset-0"
        style={{
          transform: 'skewX(-8deg)',
          backgroundColor: accentColor + '10',
          border: `1px solid ${accentColor}55`,
          borderRadius: '6px',
          boxShadow: selected
            ? `0 0 0 2px ${accentColor}80, 0 4px 20px ${accentColor}25`
            : `0 2px 8px rgba(0,0,0,0.3)`,
        }}
      />

      {/* Execution pulse overlay */}
      {data.executionStatus === 'running' && (
        <div
          className="absolute inset-0 animate-pulse pointer-events-none"
          style={{
            transform: 'skewX(-8deg)',
            backgroundColor: '#3b82f620',
            borderRadius: '6px',
          }}
        />
      )}

      {/* Content */}
      <div className="relative z-10 px-5 py-2.5 text-center select-none">
        {/* Exec status icon */}
        {es && (
          <span className={`absolute top-1 right-5 text-[10px] font-bold ${es.iconCls}`}>
            {es.icon}
          </span>
        )}

        {/* Icon + type badge row */}
        <div className="flex items-center justify-center gap-1.5 mb-1">
          <span className="text-sm leading-none">
            {TOOL_ICONS[data.toolType] || '🔧'}
          </span>
          <span className={`text-[9px] font-semibold px-1.5 py-0.5 rounded ${ts.badge}`}>
            {ts.label}
          </span>
        </div>

        {/* Tool name */}
        <p className="text-[11px] font-semibold text-slate-100 leading-tight truncate">
          {data.name}
        </p>

        {/* Description */}
        {data.description && (
          <p className="text-[9px] text-slate-400 mt-0.5 leading-tight line-clamp-2">
            {data.description}
          </p>
        )}

        {/* Execution result */}
        {data.executionResult && data.executionStatus === 'completed' && (
          <p className="text-[9px] text-green-400 mt-1">✓ {data.executionResult.duration_ms}ms</p>
        )}
        {data.executionStatus === 'failed' && (
          <p className="text-[9px] text-red-400 mt-1">✗ Failed</p>
        )}
      </div>

      {/* Source handle (bottom) */}
      <Handle type="source" position={Position.Bottom} className="!bottom-[-5px]" />
    </div>
  )
})

ToolNode.displayName = 'ToolNode'
export default ToolNode
