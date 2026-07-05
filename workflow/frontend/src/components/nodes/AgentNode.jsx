import React, { memo } from 'react'
import { Handle, Position } from 'reactflow'
import { Zap, Clock, FileSpreadsheet, Mail } from 'lucide-react'
import useStore from '../../store/workflowStore'

const TRIGGER_BADGES = {
  webhook:      { Icon: Zap,             cls: 'text-sky-300 bg-sky-900/50 border-sky-700/40',         label: 'Webhook' },
  cron:         { Icon: Clock,           cls: 'text-violet-300 bg-violet-900/50 border-violet-700/40', label: 'Cron' },
  google_sheet: { Icon: FileSpreadsheet, cls: 'text-emerald-300 bg-emerald-900/50 border-emerald-700/40', label: 'Sheet' },
  email:        { Icon: Mail,            cls: 'text-amber-300 bg-amber-900/50 border-amber-700/40',   label: 'Email' },
}

const TYPE_STYLES = {
  // Lifecycle sentinels
  start:             { border: '#22c55e', badge: 'bg-green-900/70 text-green-300',     label: 'Start' },
  end:               { border: '#f43f5e', badge: 'bg-rose-900/70 text-rose-300',       label: 'End' },
  // Core types
  automatic:         { border: '#6366f1', badge: 'bg-indigo-900/70 text-indigo-300',   label: 'Auto' },
  role_based:        { border: '#10b981', badge: 'bg-emerald-900/70 text-emerald-300', label: 'Role' },
  human_in_the_loop: { border: '#f59e0b', badge: 'bg-amber-900/70 text-amber-300',     label: 'HITL' },
  human_review:      { border: '#0ea5e9', badge: 'bg-sky-900/70 text-sky-300',         label: 'Review' },
  conditional:       { border: '#f97316', badge: 'bg-orange-900/70 text-orange-300',   label: 'Cond.' },
  parallel:          { border: '#a855f7', badge: 'bg-purple-900/70 text-purple-300',   label: 'Parallel' },
  // Advanced AI agent patterns
  prompt_agent:      { border: '#ec4899', badge: 'bg-pink-900/70 text-pink-300',       label: 'Prompt' },
  react_agent:       { border: '#06b6d4', badge: 'bg-cyan-900/70 text-cyan-300',       label: 'ReAct' },
  reflection_agent:  { border: '#14b8a6', badge: 'bg-teal-900/70 text-teal-300',       label: 'Reflect' },
  guardrails:        { border: '#ef4444', badge: 'bg-red-900/70 text-red-300',          label: 'Guard' },
  orchestrator:      { border: '#7c3aed', badge: 'bg-violet-900/70 text-violet-300',   label: 'Orchestr.' },
  supervisor:        { border: '#84cc16', badge: 'bg-lime-900/70 text-lime-300',        label: 'Supervisor' },
}

const EXEC_STYLES = {
  pending:   { ring: 'ring-slate-500/40',  icon: '○', iconCls: 'text-slate-400' },
  running:   { ring: 'ring-blue-500/60',   icon: '▶', iconCls: 'text-blue-400 animate-pulse' },
  completed: { ring: 'ring-green-500/60',  icon: '✓', iconCls: 'text-green-400' },
  failed:    { ring: 'ring-red-500/60',    icon: '✗', iconCls: 'text-red-400' },
  skipped:   { ring: 'ring-slate-500/30',  icon: '⏭', iconCls: 'text-slate-500' },
}

const TOOL_ICONS = {
  'tool-001': '🌐', 'tool-002': '⇌', 'tool-003': '✉', 'tool-004': '🗄',
  'tool-005': '📄', 'tool-006': '🧠', 'tool-007': '🛡', 'tool-008': '💬',
  'tool-009': '📊', 'tool-010': '⚡', 'tool-011': '🔌', 'tool-012': '🗃',
  'tool-013': '🔍',
}

const AgentNode = memo(({ id, data, selected }) => {
  const { tools } = useStore()
  const ts = TYPE_STYLES[data.type] || TYPE_STYLES.automatic
  const es = data.executionStatus ? EXEC_STYLES[data.executionStatus] : null
  const borderColor = data.color || ts.border

  const nodeTool = (toolId) => {
    const t = tools.find((t) => t.id === toolId)
    return t ? t.name : toolId
  }

  return (
    <div
      className={`
        relative w-56 rounded-xl overflow-hidden
        bg-slate-800/90 backdrop-blur
        border-l-4 shadow-xl
        transition-all duration-150
        ${selected ? 'ring-2 ring-indigo-400/80 shadow-indigo-500/20 shadow-2xl' : 'ring-1 ring-slate-700/50'}
        ${es ? es.ring : ''}
      `}
      style={{ borderLeftColor: borderColor }}
    >
      {/* Target handle (top) — hidden for Start nodes: nothing can connect TO Start */}
      {data.type !== 'start' && (
        <Handle
          type="target"
          position={Position.Top}
          className="!top-[-5px]"
        />
      )}

      {/* Running pulse overlay */}
      {data.executionStatus === 'running' && (
        <div className="absolute inset-0 bg-blue-500/5 animate-pulse pointer-events-none rounded-xl" />
      )}
      {data.executionStatus === 'completed' && (
        <div className="absolute inset-0 bg-green-500/5 pointer-events-none rounded-xl" />
      )}
      {data.executionStatus === 'failed' && (
        <div className="absolute inset-0 bg-red-500/5 pointer-events-none rounded-xl" />
      )}

      {/* Header */}
      <div className="px-3 pt-3 pb-2 flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded ${ts.badge}`}>
              {ts.label}
            </span>
            {es && (
              <span className={`text-xs font-bold ${es.iconCls}`} title={data.executionStatus}>
                {es.icon}
              </span>
            )}
          </div>
          <p className="text-sm font-semibold text-slate-100 truncate">{data.name}</p>
          {data.description && (
            <p className="text-[11px] text-slate-400 mt-0.5 leading-tight line-clamp-2">
              {data.description}
            </p>
          )}
        </div>
      </div>

      {/* Triggers (Start agent only) */}
      {data.type === 'start' && Array.isArray(data.properties?.triggers) && data.properties.triggers.length > 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1">
          {data.properties.triggers.map((t) => {
            const def = TRIGGER_BADGES[t.type]
            if (!def) return null
            const Icon = def.Icon
            return (
              <span
                key={t.id}
                className={`inline-flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded border ${def.cls} ${t.enabled === false ? 'opacity-40' : ''}`}
                title={`${def.label}${t.name ? ' — ' + t.name : ''}${t.enabled === false ? ' (disabled)' : ''}`}
              >
                <Icon size={9} />
                {def.label}
              </span>
            )
          })}
        </div>
      )}

      {/* Tools */}
      {data.tools && data.tools.length > 0 && (
        <div className="px-3 pb-2.5 flex flex-wrap gap-1">
          {data.tools.slice(0, 4).map((toolId) => (
            <span
              key={toolId}
              className="text-[10px] bg-slate-700/60 text-slate-300 px-1.5 py-0.5 rounded flex items-center gap-0.5"
              title={nodeTool(toolId)}
            >
              <span>{TOOL_ICONS[toolId] || '🔧'}</span>
              <span className="max-w-[64px] truncate">{nodeTool(toolId)}</span>
            </span>
          ))}
          {data.tools.length > 4 && (
            <span className="text-[10px] text-slate-500">+{data.tools.length - 4}</span>
          )}
        </div>
      )}

      {/* Execution result badge */}
      {data.executionResult && data.executionStatus !== 'running' && (
        <div className="px-3 pb-2 text-[10px] text-slate-400 border-t border-slate-700/50 pt-1.5">
          {data.executionStatus === 'completed' && (
            <span className="text-green-400">
              ✓ {data.executionResult.duration_ms}ms
            </span>
          )}
          {data.executionStatus === 'failed' && (
            <span className="text-red-400">✗ Failed</span>
          )}
          {data.executionStatus === 'skipped' && (
            <span className="text-slate-500">⏭ Skipped</span>
          )}
        </div>
      )}

      {/* Source handle (bottom) — hidden for End nodes: End cannot connect to anything */}
      {data.type !== 'end' && (
        <Handle
          type="source"
          position={Position.Bottom}
          className="!bottom-[-5px]"
        />
      )}
    </div>
  )
})

AgentNode.displayName = 'AgentNode'
export default AgentNode
