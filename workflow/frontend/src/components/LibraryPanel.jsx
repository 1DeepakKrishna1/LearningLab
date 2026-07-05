import React, { useState } from 'react'
import { GitFork, Bot, Search, Copy, ChevronDown, ChevronRight, ChevronLeft, Wrench } from 'lucide-react'
import useStore from '../store/workflowStore'

const TOOL_TYPE_COLORS = {
  api_call:       'text-sky-400',
  data_transform: 'text-teal-400',
  notification:   'text-amber-400',
  database:       'text-purple-400',
  file_io:        'text-orange-400',
  ai_inference:   'text-pink-400',
  approval:       'text-rose-400',
  webhook:        'text-cyan-400',
}

const TOOL_TYPE_LABELS = {
  api_call:       'API',
  data_transform: 'Transform',
  notification:   'Notify',
  database:       'Database',
  file_io:        'File',
  ai_inference:   'AI',
  approval:       'Approval',
  webhook:        'Webhook',
}

const TOOL_ACCENT_COLORS = {
  api_call:       '#0ea5e9',
  data_transform: '#14b8a6',
  notification:   '#f59e0b',
  database:       '#a855f7',
  file_io:        '#f97316',
  ai_inference:   '#ec4899',
  approval:       '#f43f5e',
  webhook:        '#06b6d4',
}

const TOOL_ICONS = {
  api_call: '🌐', data_transform: '⇌', notification: '✉', database: '🗄',
  file_io: '📄', ai_inference: '🧠', approval: '🛡', webhook: '⚡',
}

function ToolCard({ tool }) {
  const onDragStart = (e) => {
    e.dataTransfer.setData('application/reactflow-tool', JSON.stringify(tool))
    e.dataTransfer.effectAllowed = 'move'
  }

  const accent = TOOL_ACCENT_COLORS[tool.type] || '#0ea5e9'

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="group cursor-grab active:cursor-grabbing bg-slate-800 hover:bg-slate-700/80 border border-slate-700 hover:border-slate-500 rounded-lg p-3 transition-all select-none"
      style={{ borderLeftColor: accent, borderLeftWidth: '3px' }}
    >
      <div className="flex items-start gap-2">
        <div
          className="w-7 h-7 rounded flex items-center justify-center text-sm flex-shrink-0 mt-0.5"
          style={{ backgroundColor: accent + '20' }}
        >
          <span>{TOOL_ICONS[tool.type] || '🔧'}</span>
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[10px] font-medium text-slate-100 truncate">{tool.name}</span>
          </div>
          <span className={`text-[9px] font-semibold uppercase tracking-wide ${TOOL_TYPE_COLORS[tool.type] || 'text-slate-400'}`}>
            {TOOL_TYPE_LABELS[tool.type] || tool.type}
          </span>
          <p className="text-[10px] text-slate-400 mt-0.5 leading-tight line-clamp-2">{tool.description}</p>
        </div>
      </div>
      <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        <p className="text-[9px] text-slate-500 text-center">↕ Drag to canvas</p>
      </div>
    </div>
  )
}

const AGENT_TYPE_COLORS = {
  // Lifecycle sentinels
  start:             'text-green-400',
  end:               'text-rose-400',
  // Core types
  automatic:         'text-indigo-400',
  role_based:        'text-emerald-400',
  human_in_the_loop: 'text-amber-400',
  human_review:      'text-sky-400',
  conditional:       'text-orange-400',
  parallel:          'text-purple-400',
  // Advanced AI agent patterns
  prompt_agent:      'text-pink-400',
  react_agent:       'text-cyan-400',
  reflection_agent:  'text-teal-400',
  guardrails:        'text-red-400',
  orchestrator:      'text-violet-400',
  supervisor:        'text-lime-400',
}

const AGENT_TYPE_LABELS = {
  // Lifecycle sentinels
  start:             'Start',
  end:               'End',
  // Core types
  automatic:         'Auto',
  role_based:        'Role',
  human_in_the_loop: 'HITL',
  human_review:      'Review',
  conditional:       'Cond.',
  parallel:          'Parallel',
  // Advanced AI agent patterns
  prompt_agent:      'Prompt',
  react_agent:       'ReAct',
  reflection_agent:  'Reflect',
  guardrails:        'Guard',
  orchestrator:      'Orchestr.',
  supervisor:        'Supervisor',
}

function AgentCard({ agent }) {
  const onDragStart = (e) => {
    e.dataTransfer.setData('application/reactflow-agent', JSON.stringify(agent))
    e.dataTransfer.effectAllowed = 'move'
  }

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="group cursor-grab active:cursor-grabbing bg-slate-800 hover:bg-slate-700/80 border border-slate-700 hover:border-slate-500 rounded-lg p-3 transition-all select-none"
    >
      <div className="flex items-start gap-2">
        <div
          className="w-7 h-7 rounded-md flex items-center justify-center text-sm flex-shrink-0 mt-0.5"
          style={{ backgroundColor: (agent.color || '#6366f1') + '25', borderColor: agent.color || '#6366f1', border: '1px solid' }}
        >
          <Bot size={14} className="opacity-80" style={{ color: agent.color || '#6366f1' }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-[10px] font-medium text-slate-100 truncate">{agent.name}</span>
          </div>
          <span className={`text-[9px] font-semibold uppercase tracking-wide ${AGENT_TYPE_COLORS[agent.type] || 'text-slate-400'}`}>
            {AGENT_TYPE_LABELS[agent.type] || agent.type}
          </span>
          <p className="text-[10px] text-slate-400 mt-0.5 leading-tight line-clamp-2">{agent.description}</p>
          {agent.tools?.length > 0 && (
            <p className="text-[10px] text-slate-500 mt-1">{agent.tools.length} tool{agent.tools.length !== 1 ? 's' : ''}</p>
          )}
        </div>
      </div>
      <div className="mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
        {(agent.type === 'start' || agent.type === 'end') ? (
          <p className="text-[9px] text-center" style={{ color: agent.type === 'start' ? '#86efac' : '#fda4af' }}>
            ↕ Drag to canvas · 1 per workflow
          </p>
        ) : (
          <p className="text-[9px] text-slate-500 text-center">↕ Drag to canvas</p>
        )}
      </div>
    </div>
  )
}

function WorkflowCard({ workflow }) {
  const { cloneWorkflow, loadWorkflow } = useStore()

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-lg p-3 group">
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-100 truncate">{workflow.name}</p>
          <p className="text-[11px] text-slate-400 mt-0.5 leading-tight line-clamp-2">{workflow.description}</p>
        </div>
        <GitFork size={14} className="text-slate-500 flex-shrink-0 mt-0.5" />
      </div>

      {workflow.tags?.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2">
          {workflow.tags.map((tag) => (
            <span key={tag} className="text-[9px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">
              {tag}
            </span>
          ))}
        </div>
      )}

      <div className="flex gap-1.5">
        <button
          onClick={() => cloneWorkflow(workflow.id)}
          className="flex-1 flex items-center justify-center gap-1 text-[11px] bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-600/30 rounded px-2 py-1 transition-colors"
        >
          <Copy size={10} />
          Clone
        </button>
        <button
          onClick={() => loadWorkflow(workflow.id)}
          className="flex-1 text-[11px] bg-slate-700/50 hover:bg-slate-600/50 text-slate-300 border border-slate-600/50 rounded px-2 py-1 transition-colors"
        >
          Preview
        </button>
      </div>
    </div>
  )
}

export default function LibraryPanel({ collapsed = false, onToggle = () => {} }) {
  const [tab, setTab] = useState('agents')
  const [search, setSearch] = useState('')
  const [agentsOpen, setAgentsOpen] = useState(true)
  const { libraryWorkflows, libraryAgents, tools } = useStore()

  if (collapsed) {
    return (
      <aside className="w-8 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col items-center py-2 gap-2">
        <button
          onClick={onToggle}
          title="Show Library"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
        >
          <ChevronRight size={14} />
        </button>
        <span className="text-[10px] text-slate-600 font-medium tracking-widest" style={{ writingMode: 'vertical-rl', transform: 'rotate(180deg)' }}>
          LIBRARY
        </span>
      </aside>
    )
  }

  const filteredAgents = libraryAgents.filter(
    (a) =>
      a.name.toLowerCase().includes(search.toLowerCase()) ||
      a.description.toLowerCase().includes(search.toLowerCase())
  )

  const filteredTools = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description?.toLowerCase().includes(search.toLowerCase())
  )

  const filteredWorkflows = libraryWorkflows.filter(
    (w) =>
      w.name.toLowerCase().includes(search.toLowerCase()) ||
      w.description?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <aside className="w-72 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col overflow-hidden">
      {/* Panel header */}
      <div className="px-4 py-3 border-b border-slate-800">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-sm font-semibold text-slate-200">Library</h2>
          <button
            onClick={onToggle}
            title="Hide Library"
            className="p-1 text-slate-500 hover:text-white hover:bg-slate-700 rounded transition-colors"
          >
            <ChevronLeft size={13} />
          </button>
        </div>
        <div className="relative">
          <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            type="text"
            placeholder="Search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-md pl-7 pr-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>

        <div className="flex mt-2 bg-slate-800 rounded-lg p-0.5 gap-0.5">
          {['agents', 'tools', 'workflows'].map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 text-xs py-1 rounded-md transition-colors capitalize ${
                tab === t ? 'bg-indigo-600 text-white font-medium' : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Panel body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2">
        {tab === 'agents' && (
          <>
            <div
              className="flex items-center gap-1 text-[11px] text-slate-400 cursor-pointer hover:text-slate-200 mb-1 select-none"
              onClick={() => setAgentsOpen((v) => !v)}
            >
              {agentsOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
              <Bot size={11} />
              <span className="font-medium uppercase tracking-wide">Agents ({filteredAgents.length})</span>
            </div>
            {agentsOpen &&
              (filteredAgents.length > 0 ? (
                filteredAgents.map((a) => <AgentCard key={a.id} agent={a} />)
              ) : (
                <p className="text-xs text-slate-600 text-center py-4">No agents match</p>
              ))}
          </>
        )}

        {tab === 'tools' && (
          <>
            <p className="text-[11px] text-slate-500 mb-1 flex items-center gap-1">
              <Wrench size={11} />
              <span className="uppercase tracking-wide font-medium">Tools ({filteredTools.length})</span>
            </p>
            {filteredTools.length > 0 ? (
              filteredTools.map((t) => <ToolCard key={t.id} tool={t} />)
            ) : (
              <p className="text-xs text-slate-600 text-center py-4">No tools match</p>
            )}
          </>
        )}

        {tab === 'workflows' && (
          <>
            <p className="text-[11px] text-slate-500 mb-1 flex items-center gap-1">
              <GitFork size={11} />
              <span className="uppercase tracking-wide font-medium">Templates ({filteredWorkflows.length})</span>
            </p>
            {filteredWorkflows.length > 0 ? (
              filteredWorkflows.map((w) => <WorkflowCard key={w.id} workflow={w} />)
            ) : (
              <p className="text-xs text-slate-600 text-center py-4">No templates match</p>
            )}
          </>
        )}
      </div>
    </aside>
  )
}
