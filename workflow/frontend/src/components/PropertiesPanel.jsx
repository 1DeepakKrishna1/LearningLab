import { useState, useEffect, useRef, useCallback } from 'react'
import { X, Trash2, Save, ChevronDown, ChevronUp, Search, Settings2, ChevronLeft, ChevronRight, Plus, Zap, Clock, FileSpreadsheet, Mail, Copy, Check } from 'lucide-react'
import useStore from '../store/workflowStore'
import { triggerBaseUrl } from '../api/api'

const AGENT_TYPES = [
  // Lifecycle sentinels
  { value: 'start',             label: 'Start' },
  { value: 'end',               label: 'End' },
  // Core types
  { value: 'automatic',         label: 'Automatic' },
  { value: 'role_based',        label: 'Role-Based' },
  { value: 'human_in_the_loop', label: 'Human In The Loop' },
  { value: 'human_review',      label: 'Human Review' },
  { value: 'conditional',       label: 'Conditional' },
  { value: 'parallel',          label: 'Parallel' },
  // Advanced AI agent patterns
  { value: 'prompt_agent',      label: 'Prompt Agent' },
  { value: 'react_agent',       label: 'ReAct (Reason + Act)' },
  { value: 'reflection_agent',  label: 'Reflection' },
  { value: 'guardrails',        label: 'Guardrails' },
  { value: 'orchestrator',      label: 'Orchestrator' },
  { value: 'supervisor',        label: 'Supervisor' },
]

const EXEC_STATUS_STYLES = {
  completed: 'text-green-400 bg-green-900/30 border-green-700/50',
  failed:    'text-red-400 bg-red-900/30 border-red-700/50',
  running:   'text-blue-400 bg-blue-900/30 border-blue-700/50 animate-pulse',
  pending:   'text-slate-400 bg-slate-800/50 border-slate-700/50',
  skipped:   'text-slate-500 bg-slate-800/30 border-slate-700/30',
}

// ── Prompt field helpers ──────────────────────────────────

/** Keys whose values are prompt/template text requiring the PromptTextarea */
const isPromptField = (key) => /_prompt$|_template$|schema_description$/.test(key)

const COMMON_VARS = [
  { label: 'input_data',       desc: 'Data from previous node' },
  { label: 'context',          desc: 'Workflow execution context' },
  { label: 'user_query',       desc: "User's original question" },
  { label: 'previous_output',  desc: 'Output from previous step' },
  { label: 'json_data',        desc: 'Structured JSON payload' },
  { label: 'records',          desc: 'List of data records' },
  { label: 'domain',           desc: 'Topic or domain area' },
  { label: 'task',             desc: 'Current task description' },
  { label: 'timestamp',        desc: 'Current date/time' },
  { label: 'workflow_name',    desc: 'Name of this workflow' },
  { label: 'status',           desc: 'Execution status' },
  { label: 'output_format',    desc: 'Desired output format' },
  { label: 'db_schema',        desc: 'Database table definitions' },
  { label: 'db_relationships', desc: 'Table FK relationships' },
  { label: 'table_name',       desc: 'Target table name' },
  { label: 'columns',          desc: 'Column list (comma-sep)' },
  { label: 'filter_field',     desc: 'Column name for filtering' },
  { label: 'filter_value',     desc: 'Value to filter by' },
  { label: 'max_rows',         desc: 'Row limit for results' },
  { label: 'duration_ms',      desc: 'Step duration in ms' },
]

/**
 * Auto-resizing textarea with:
 * - detected {{variable}} chips
 * - "Insert variable" dropdown (inserts at cursor)
 */
function PromptTextarea({ value, onChange }) {
  const ref  = useRef(null)
  const [open, setOpen] = useState(false)

  // Auto-resize whenever content changes
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 320) + 'px'
  }, [value])

  // Close dropdown when clicking outside
  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (!e.target.closest('[data-prompt-dropdown]')) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const detected = [...new Set(
    [...String(value || '').matchAll(/\{\{([^}]+)\}\}/g)].map(m => m[1].trim())
  )]

  const insert = (varName) => {
    const el    = ref.current
    const text  = String(value || '')
    const start = el ? (el.selectionStart ?? text.length) : text.length
    const end   = el ? (el.selectionEnd   ?? start)       : start
    const snip  = `{{${varName}}}`
    onChange(text.slice(0, start) + snip + text.slice(end))
    setOpen(false)
    requestAnimationFrame(() => {
      if (!el) return
      el.focus()
      el.setSelectionRange(start + snip.length, start + snip.length)
    })
  }

  return (
    <div>
      <textarea
        ref={ref}
        value={String(value || '')}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors font-mono leading-relaxed"
        style={{ minHeight: '72px', maxHeight: '320px', resize: 'vertical', overflow: 'auto' }}
        spellCheck={false}
      />

      {/* Detected variable chips */}
      {detected.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {detected.map(v => (
            <span
              key={v}
              className="text-[9px] bg-indigo-900/50 text-indigo-300 border border-indigo-700/40 px-1.5 py-0.5 rounded font-mono"
            >
              {`{{${v}}}`}
            </span>
          ))}
        </div>
      )}

      {/* Insert variable button + dropdown */}
      <div className="relative mt-1.5" data-prompt-dropdown>
        <button
          type="button"
          onClick={() => setOpen(o => !o)}
          className="text-[10px] text-slate-500 hover:text-indigo-400 transition-colors flex items-center gap-1"
        >
          <span className="font-mono font-bold text-[11px]">{'{}'}</span>
          Insert variable
        </button>

        {open && (
          <div className="absolute left-0 top-6 z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-2xl p-1.5 w-64 max-h-56 overflow-y-auto">
            <p className="text-[9px] text-slate-500 uppercase tracking-wide font-semibold mb-1 px-1.5">
              Common variables
            </p>
            {COMMON_VARS.map(v => (
              <button
                key={v.label}
                onClick={() => insert(v.label)}
                className="w-full text-left px-2 py-1 rounded hover:bg-slate-700 transition-colors group flex items-baseline gap-1.5"
              >
                <span className="text-[10px] font-mono text-indigo-300 group-hover:text-indigo-200 flex-shrink-0">
                  {`{{${v.label}}}`}
                </span>
                <span className="text-[9px] text-slate-500 truncate">{v.desc}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Generic field wrapper ─────────────────────────────────

function Section({ title, defaultOpen = true, children }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="border border-slate-700/50 rounded-lg overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-3 py-2 bg-slate-800/50 hover:bg-slate-700/30 transition-colors"
      >
        <span className="text-[11px] font-semibold text-slate-300 uppercase tracking-wide">{title}</span>
        {open ? <ChevronUp size={12} className="text-slate-500" /> : <ChevronDown size={12} className="text-slate-500" />}
      </button>
      {open && <div className="p-3 space-y-2">{children}</div>}
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div>
      <label className="block text-[10px] text-slate-400 mb-0.5 uppercase tracking-wide">{label}</label>
      {children}
    </div>
  )
}

/** Renders a single property value — prompt fields get PromptTextarea, others get appropriate inputs. */
function PropValue({ propKey, val, onChange }) {
  if (typeof val === 'boolean') {
    return (
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={val}
          onChange={e => onChange(e.target.checked)}
          className="accent-indigo-500"
        />
        <span className="text-xs text-slate-300">{val ? 'Enabled' : 'Disabled'}</span>
      </div>
    )
  }
  if (typeof val === 'number') {
    return (
      <input
        type="number"
        value={val}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
      />
    )
  }
  if (typeof val === 'string' && isPromptField(propKey)) {
    return <PromptTextarea value={val} onChange={onChange} />
  }
  if (typeof val === 'string') {
    return (
      <input
        type="text"
        value={val}
        onChange={e => onChange(e.target.value)}
        className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
      />
    )
  }
  return <span className="text-[10px] text-slate-500">{JSON.stringify(val)}</span>
}

/** Renders editable fields for a tool's properties merged with per-agent overrides. */
function ToolConfigEditor({ tool, overrides, onChange }) {
  const merged = { ...tool.properties, ...overrides }
  if (Object.keys(merged).length === 0) {
    return <p className="text-[10px] text-slate-500 italic">No configurable properties.</p>
  }
  return (
    <div className="space-y-2 mt-2 pt-2 border-t border-slate-700/40">
      <p className="text-[9px] text-slate-500 uppercase tracking-wide font-semibold">Per-agent overrides</p>
      {Object.entries(merged).map(([key, val]) => {
        const overrideVal = overrides?.[key] ?? val
        return (
          <div key={key}>
            <label className="block text-[10px] text-slate-400 mb-0.5 uppercase tracking-wide">
              {key.replace(/_/g, ' ')}
              {overrides?.[key] !== undefined && (
                <span className="ml-1 text-indigo-400 normal-case">(overridden)</span>
              )}
            </label>
            <PropValue
              propKey={key}
              val={typeof overrideVal === typeof val ? overrideVal : val}
              onChange={v => onChange(key, v)}
            />
          </div>
        )
      })}
    </div>
  )
}

// ── Invoke tab components ─────────────────────────────────

const WF_VAR_OPTIONS = [
  { value: '{{wf.status}}',      label: 'wf.status',      desc: 'Workflow execution status' },
  { value: '{{wf.token_limit}}', label: 'wf.token_limit', desc: 'Token limit configured' },
  { value: '{{wf.timetaken}}',   label: 'wf.timetaken',   desc: 'Elapsed execution time (ms)' },
]

const TOOL_OUTPUT_FIELDS = ['output', 'result', 'status', 'data', 'response', 'value', 'processed', 'rows_returned']

const VALUE_TYPE_LABELS = {
  constant:   'Constant',
  workflow:   'Workflow',
  tool:       'Tool Output',
  data_model: 'Data Model',
}

function InvokeValueEditor({ param, onChange, dataModel, nodes }) {
  const { value_type, value } = param

  if (value_type === 'constant') {
    return (
      <input
        type="text"
        value={value}
        onChange={e => onChange({ value: e.target.value })}
        placeholder="123  or  &quot;Approved&quot;  or  12/05/2026"
        className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
      />
    )
  }

  if (value_type === 'workflow') {
    return (
      <div className="flex gap-1">
        <input
          type="text"
          value={value}
          onChange={e => onChange({ value: e.target.value })}
          placeholder="{{wf.status}}"
          className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
        />
        <select
          defaultValue=""
          onChange={e => { if (e.target.value) { onChange({ value: e.target.value }); e.target.value = '' } }}
          className="bg-slate-900 border border-slate-700 rounded px-1 py-1 text-[10px] text-slate-400 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          title="Pick workflow variable"
        >
          <option value="">↗</option>
          {WF_VAR_OPTIONS.map(v => (
            <option key={v.value} value={v.value}>{v.label}</option>
          ))}
        </select>
      </div>
    )
  }

  if (value_type === 'tool') {
    const toolOptions = (nodes || [])
      .filter(n => n.data?.name)
      .flatMap(n => {
        const safeName = n.data.name.replace(/\s+/g, '_')
        return TOOL_OUTPUT_FIELDS.map(f => ({
          value: `{{tool.${safeName}.${f}}}`,
          label: `${n.data.name} → ${f}`,
        }))
      })
    return (
      <div className="space-y-1">
        <input
          type="text"
          value={value}
          onChange={e => onChange({ value: e.target.value })}
          placeholder="{{tool.ToolName.output}}"
          className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
        />
        {toolOptions.length > 0 && (
          <select
            defaultValue=""
            onChange={e => { if (e.target.value) { onChange({ value: e.target.value }); e.target.value = '' } }}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[10px] text-slate-400 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          >
            <option value="">Pick from workflow agents/tools…</option>
            {toolOptions.map(o => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        )}
      </div>
    )
  }

  if (value_type === 'data_model') {
    if (!dataModel) {
      return (
        <p className="text-[10px] text-slate-500 italic bg-slate-900 border border-slate-700/50 rounded px-2 py-1">
          Associate a Data Model with this workflow to use this source type.
        </p>
      )
    }
    const dmMatch = (value || '').match(/^\{\{([^.}]+)\.([^}]+)\}\}$/)
    const selEntity = dmMatch?.[1] || ''
    const selField  = dmMatch?.[2] || ''
    const entityObj = dataModel.entities?.find(e => e.name === selEntity)

    return (
      <div className="flex gap-1">
        <select
          value={selEntity}
          onChange={e => {
            const ent = e.target.value
            if (!ent) { onChange({ value: '' }); return }
            const entObj = dataModel.entities?.find(x => x.name === ent)
            const firstField = entObj?.fields?.[0]?.name || ''
            onChange({ value: firstField ? `{{${ent}.${firstField}}}` : '' })
          }}
          className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors"
        >
          <option value="">Entity…</option>
          {(dataModel.entities || []).map(e => (
            <option key={e.name} value={e.name}>{e.name}</option>
          ))}
        </select>
        <select
          value={selField}
          disabled={!entityObj}
          onChange={e => {
            if (selEntity && e.target.value) onChange({ value: `{{${selEntity}.${e.target.value}}}` })
          }}
          className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors disabled:opacity-40"
        >
          <option value="">Field…</option>
          {(entityObj?.fields || []).map(f => (
            <option key={f.name} value={f.name}>{f.name}</option>
          ))}
        </select>
      </div>
    )
  }

  return null
}

function InvokeParamRow({ param, idx, section, onUpdate, onRemove, dataModel, nodes }) {
  return (
    <div className="bg-slate-800/60 rounded-lg border border-slate-700/40 p-2.5 space-y-2">
      <div className="flex gap-2 items-start">
        <div className="flex-1 min-w-0">
          <label className="block text-[9px] text-slate-500 uppercase tracking-wide mb-0.5">Name</label>
          <input
            type="text"
            value={param.name}
            onChange={e => onUpdate(idx, { name: e.target.value })}
            placeholder="parameter_name"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div className="flex-1 min-w-0">
          <label className="block text-[9px] text-slate-500 uppercase tracking-wide mb-0.5">
            {section === 'input_parameters' ? 'Source' : 'Target'}
          </label>
          <select
            value={param.value_type}
            onChange={e => onUpdate(idx, { value_type: e.target.value, value: '' })}
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors"
          >
            {Object.entries(VALUE_TYPE_LABELS).map(([k, v]) => (
              <option key={k} value={k}>{v}</option>
            ))}
          </select>
        </div>
        <button
          onClick={() => onRemove(idx)}
          className="mt-4 p-1 text-slate-600 hover:text-red-400 transition-colors flex-shrink-0"
          title="Remove parameter"
        >
          <X size={12} />
        </button>
      </div>

      <div>
        <label className="block text-[9px] text-slate-500 uppercase tracking-wide mb-0.5">Value</label>
        <InvokeValueEditor
          param={param}
          onChange={patch => onUpdate(idx, patch)}
          dataModel={dataModel}
          nodes={nodes}
        />
      </div>

      {param.name && (
        <p className="text-[9px] text-indigo-400/60 font-mono">
          Reference: {'{{'}wf.{param.name}{'}}'}
        </p>
      )}
    </div>
  )
}

function InvokeTab({ localData, onPatch, dataModels, currentAssociation, nodes }) {
  const invoke = localData.invoke || { input_parameters: [], output_parameters: [] }

  const dataModel = currentAssociation?.data_model_id
    ? dataModels?.find(dm => dm.id === currentAssociation.data_model_id)
    : null

  function updateSection(section, list) {
    onPatch('invoke', { ...invoke, [section]: list })
  }

  function addParam(section) {
    updateSection(section, [...(invoke[section] || []), { name: '', value_type: 'constant', value: '' }])
  }

  function updateParam(section, idx, patch) {
    const list = [...(invoke[section] || [])]
    list[idx] = { ...list[idx], ...patch }
    updateSection(section, list)
  }

  function removeParam(section, idx) {
    const list = [...(invoke[section] || [])]
    list.splice(idx, 1)
    updateSection(section, list)
  }

  const inputParams  = invoke.input_parameters  || []
  const outputParams = invoke.output_parameters || []

  return (
    <div className="space-y-3">
      {/* Data model indicator */}
      {dataModel ? (
        <div className="flex items-center gap-1.5 text-[10px] bg-indigo-900/20 border border-indigo-700/30 rounded-lg px-2.5 py-1.5 text-indigo-300">
          <span className="text-indigo-500">◈</span>
          Data Model: <span className="font-medium">{dataModel.name}</span>
        </div>
      ) : (
        <div className="text-[10px] text-slate-500 bg-slate-800/40 border border-slate-700/30 rounded-lg px-2.5 py-1.5 leading-relaxed">
          No Data Model linked to this workflow. Open Save → Association to link one, enabling Data Model source type.
        </div>
      )}

      {/* Input parameters */}
      <Section title={`Input Parameters (${inputParams.length})`} defaultOpen>
        <p className="text-[10px] text-slate-500 mb-2 leading-relaxed">
          Values resolved and passed into this agent at runtime. Reference using{' '}
          <span className="font-mono text-indigo-400/80">{'{{'}wf.name{'}}'}</span>
        </p>
        <div className="space-y-2">
          {inputParams.map((param, idx) => (
            <InvokeParamRow
              key={idx}
              param={param}
              idx={idx}
              section="input_parameters"
              onUpdate={(i, patch) => updateParam('input_parameters', i, patch)}
              onRemove={i => removeParam('input_parameters', i)}
              dataModel={dataModel}
              nodes={nodes}
            />
          ))}
        </div>
        <button
          onClick={() => addParam('input_parameters')}
          className="w-full mt-2 flex items-center justify-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 border border-dashed border-indigo-700/40 hover:border-indigo-500/60 rounded-lg py-1.5 transition-colors"
        >
          <Plus size={11} /> Add Input Parameter
        </button>
      </Section>

      {/* Output parameters */}
      <Section title={`Output Parameters (${outputParams.length})`} defaultOpen>
        <p className="text-[10px] text-slate-500 mb-2 leading-relaxed">
          Values captured from agent output and persisted to the Data Model instance.
        </p>
        <div className="space-y-2">
          {outputParams.map((param, idx) => (
            <InvokeParamRow
              key={idx}
              param={param}
              idx={idx}
              section="output_parameters"
              onUpdate={(i, patch) => updateParam('output_parameters', i, patch)}
              onRemove={i => removeParam('output_parameters', i)}
              dataModel={dataModel}
              nodes={nodes}
            />
          ))}
        </div>
        <button
          onClick={() => addParam('output_parameters')}
          className="w-full mt-2 flex items-center justify-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 border border-dashed border-indigo-700/40 hover:border-indigo-500/60 rounded-lg py-1.5 transition-colors"
        >
          <Plus size={11} /> Add Output Parameter
        </button>
      </Section>
    </div>
  )
}

// ── Triggers (Start agent only) ───────────────────────────

const TRIGGER_DEFS = {
  webhook: {
    label: 'HTTP Webhook',
    icon: Zap,
    color: 'sky',
    description: 'Fire the workflow from any external POST request.',
    defaultConfig: { secret: '' },
  },
  cron: {
    label: 'Cron Schedule',
    icon: Clock,
    color: 'violet',
    description: 'Fire on a recurring schedule (5-field cron expression).',
    defaultConfig: { expression: '*/5 * * * *' },
  },
  google_sheet: {
    label: 'Google Sheet Row',
    icon: FileSpreadsheet,
    color: 'emerald',
    description: 'Fire when a Google Apps Script posts a new row.',
    defaultConfig: { sheet_id: '', secret: '' },
  },
  email: {
    label: 'Email (Power Automate)',
    icon: Mail,
    color: 'amber',
    description: 'Fire when a Power Automate flow forwards an email.',
    defaultConfig: { subject_contains: '', from_contains: '', secret: '' },
  },
}

const TRIGGER_COLOR_CLS = {
  sky:     { tag: 'bg-sky-900/60 text-sky-300 border-sky-700/50',         text: 'text-sky-300' },
  violet:  { tag: 'bg-violet-900/60 text-violet-300 border-violet-700/50', text: 'text-violet-300' },
  emerald: { tag: 'bg-emerald-900/60 text-emerald-300 border-emerald-700/50', text: 'text-emerald-300' },
  amber:   { tag: 'bg-amber-900/60 text-amber-300 border-amber-700/50',   text: 'text-amber-300' },
}

function _newTrigger(type) {
  const def = TRIGGER_DEFS[type]
  return {
    id: `trg-${Math.random().toString(36).slice(2, 10)}`,
    type,
    name: def.label,
    enabled: true,
    config: { ...def.defaultConfig },
  }
}

function _externalUrl(trigger, workflowId) {
  if (!workflowId) return null
  const base = triggerBaseUrl()
  if (trigger.type === 'webhook')      return `${base}/triggers/webhook/${workflowId}/${trigger.id}`
  if (trigger.type === 'google_sheet') return `${base}/triggers/google-sheet/${workflowId}/${trigger.id}`
  if (trigger.type === 'email')        return `${base}/triggers/email/${workflowId}/${trigger.id}`
  return null
}

function CopyableUrl({ url }) {
  const [copied, setCopied] = useState(false)
  if (!url) return null
  return (
    <div className="flex items-center gap-1 bg-slate-900 border border-slate-700/50 rounded px-2 py-1.5">
      <code className="flex-1 text-[10px] text-slate-300 font-mono truncate select-all" title={url}>
        {url}
      </code>
      <button
        onClick={() => {
          navigator.clipboard?.writeText(url)
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        }}
        className="p-1 text-slate-500 hover:text-indigo-300 transition-colors flex-shrink-0"
        title="Copy URL"
      >
        {copied ? <Check size={11} className="text-green-400" /> : <Copy size={11} />}
      </button>
    </div>
  )
}

function TriggerCard({ trigger, idx, workflowId, onPatch, onRemove }) {
  const def = TRIGGER_DEFS[trigger.type]
  if (!def) return null
  const Icon = def.icon
  const colors = TRIGGER_COLOR_CLS[def.color]
  const url = _externalUrl(trigger, workflowId)

  const patchField = (k, v) => onPatch(idx, { ...trigger, [k]: v })
  const patchCfg   = (k, v) => onPatch(idx, { ...trigger, config: { ...(trigger.config || {}), [k]: v } })

  return (
    <div className={`rounded-lg border ${trigger.enabled ? 'bg-slate-800/60 border-slate-700/60' : 'bg-slate-900/40 border-slate-800 opacity-60'} p-2.5 space-y-2`}>
      <div className="flex items-center gap-2">
        <span className={`inline-flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded border ${colors.tag}`}>
          <Icon size={10} />
          {def.label}
        </span>
        <input
          type="text"
          value={trigger.name || ''}
          onChange={(e) => patchField('name', e.target.value)}
          placeholder="Trigger name"
          className="flex-1 min-w-0 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
        />
        <label className="flex items-center gap-1 text-[10px] text-slate-400" title="Enable/disable">
          <input
            type="checkbox"
            checked={trigger.enabled !== false}
            onChange={(e) => patchField('enabled', e.target.checked)}
            className="accent-indigo-500"
          />
        </label>
        <button onClick={() => onRemove(idx)} className="p-1 text-slate-600 hover:text-red-400 transition-colors" title="Remove trigger">
          <X size={11} />
        </button>
      </div>

      <p className="text-[10px] text-slate-500 leading-relaxed">{def.description}</p>

      {/* Type-specific config */}
      {trigger.type === 'cron' && (
        <Field label="Cron Expression (m h dom mon dow)">
          <input
            type="text"
            value={trigger.config?.expression || ''}
            onChange={(e) => patchCfg('expression', e.target.value)}
            placeholder="*/5 * * * *"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 font-mono focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <p className="text-[9px] text-slate-500 mt-1">e.g. <code>*/5 * * * *</code> every 5 min · <code>0 9 * * 1</code> 9am every Monday</p>
        </Field>
      )}

      {trigger.type === 'google_sheet' && (
        <Field label="Sheet ID (optional filter)">
          <input
            type="text"
            value={trigger.config?.sheet_id || ''}
            onChange={(e) => patchCfg('sheet_id', e.target.value)}
            placeholder="1A2B3C…"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </Field>
      )}

      {trigger.type === 'email' && (
        <>
          <Field label="Subject contains (optional)">
            <input
              type="text"
              value={trigger.config?.subject_contains || ''}
              onChange={(e) => patchCfg('subject_contains', e.target.value)}
              placeholder="Invoice"
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </Field>
          <Field label="From contains (optional)">
            <input
              type="text"
              value={trigger.config?.from_contains || ''}
              onChange={(e) => patchCfg('from_contains', e.target.value)}
              placeholder="finance@"
              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
            />
          </Field>
        </>
      )}

      {(trigger.type === 'webhook' || trigger.type === 'google_sheet' || trigger.type === 'email') && (
        <Field label="Shared Secret (optional)">
          <input
            type="text"
            value={trigger.config?.secret || ''}
            onChange={(e) => patchCfg('secret', e.target.value)}
            placeholder="random-string"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-[11px] text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition-colors"
          />
          <p className="text-[9px] text-slate-500 mt-1">Sent as <code>X-Trigger-Secret</code> header or <code>?secret=</code> query.</p>
        </Field>
      )}

      {url && (
        <div>
          <p className="text-[9px] text-slate-500 uppercase tracking-wide mb-1">External URL</p>
          {workflowId ? (
            <CopyableUrl url={url} />
          ) : (
            <p className="text-[10px] text-amber-400/80 italic">Save the workflow to get a callable URL.</p>
          )}
        </div>
      )}
    </div>
  )
}

function TriggersSection({ triggers, workflowId, onChange }) {
  const list = Array.isArray(triggers) ? triggers : []
  // Open by default only when triggers are already configured. Otherwise stay
  // collapsed so the section is opt-in and doesn't crowd the Start config.
  const hasAny = list.length > 0

  const add = (type) => onChange([...list, _newTrigger(type)])
  const patch = (idx, next) => onChange(list.map((t, i) => i === idx ? next : t))
  const remove = (idx) => onChange(list.filter((_, i) => i !== idx))

  return (
    <Section title={`Triggers (${list.length}) — optional`} defaultOpen={hasAny}>
      <p className="text-[10px] text-slate-400 mb-2 leading-relaxed">
        <span className="text-slate-300 font-medium">Optional.</span> Without any trigger this workflow still runs from the toolbar <code>Run</code> button. Add triggers to also fire from webhooks, cron, Google Sheets, or Power Automate. The <code>Run with…</code> dropdown can simulate any trigger type regardless of what's saved here.
      </p>

      <div className="space-y-2">
        {list.map((t, i) => (
          <TriggerCard
            key={t.id || i}
            trigger={t}
            idx={i}
            workflowId={workflowId}
            onPatch={patch}
            onRemove={remove}
          />
        ))}
      </div>

      <div className="mt-2 grid grid-cols-2 gap-1.5">
        {Object.entries(TRIGGER_DEFS).map(([type, def]) => {
          const Icon = def.icon
          const colors = TRIGGER_COLOR_CLS[def.color]
          return (
            <button
              key={type}
              onClick={() => add(type)}
              className={`flex items-center gap-1.5 text-[10px] ${colors.text} hover:bg-slate-800 border border-dashed border-slate-700 hover:border-slate-600 rounded-lg px-2 py-1.5 transition-colors`}
            >
              <Icon size={11} />
              <span className="truncate">Add {def.label}</span>
            </button>
          )
        })}
      </div>
    </Section>
  )
}


export default function PropertiesPanel({ collapsed = false, onToggle = () => {} }) {
  const { selectedNode, tools, nodes, updateNodeData, deleteNode, setSelectedNode, saveWorkflow, dataModels, currentAssociation } = useStore()
  const [localData, setLocalData] = useState(null)
  const [tab, setTab] = useState('properties')
  const [toolSearch, setToolSearch] = useState('')
  const [expandedToolId, setExpandedToolId] = useState(null)
  const [panelWidth, setPanelWidth] = useState(320)
  const isResizingRef = useRef(false)
  const startXRef = useRef(0)
  const startWidthRef = useRef(320)

  const onMouseMove = useCallback((e) => {
    if (!isResizingRef.current) return
    const delta = startXRef.current - e.clientX
    setPanelWidth(Math.min(600, Math.max(240, startWidthRef.current + delta)))
  }, [])

  const onMouseUp = useCallback(() => {
    isResizingRef.current = false
    document.removeEventListener('mousemove', onMouseMove)
    document.removeEventListener('mouseup', onMouseUp)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
  }, [onMouseMove])

  const startResize = useCallback((e) => {
    isResizingRef.current = true
    startXRef.current = e.clientX
    startWidthRef.current = panelWidth
    document.addEventListener('mousemove', onMouseMove)
    document.addEventListener('mouseup', onMouseUp)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
    e.preventDefault()
  }, [panelWidth, onMouseMove, onMouseUp])

  useEffect(() => {
    if (selectedNode) {
      setLocalData({ ...selectedNode.data })
      setTab(selectedNode.data.executionResult ? 'execution' : 'properties')
      setExpandedToolId(null)
    } else {
      setLocalData(null)
    }
  }, [selectedNode])

  if (collapsed) {
    return (
      <aside className="w-8 flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col items-center py-2 gap-2">
        <button
          onClick={onToggle}
          title="Show Properties"
          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700 rounded transition-colors"
        >
          <ChevronLeft size={14} />
        </button>
        <span className="text-[10px] text-slate-600 font-medium tracking-widest" style={{ writingMode: 'vertical-rl' }}>
          PROPERTIES
        </span>
      </aside>
    )
  }

  if (!selectedNode || !localData) {
    return (
      <aside
        className="flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden relative"
        style={{ width: panelWidth }}
      >
        {/* Resize handle */}
        <div
          onMouseDown={startResize}
          className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500/60 transition-colors z-10"
        />
        {/* Collapse button */}
        <div className="px-3 py-2 border-b border-slate-800 flex justify-between items-center">
          <span className="text-xs text-slate-500 font-medium">Properties</span>
          <button
            onClick={onToggle}
            title="Hide Properties"
            className="p-1 text-slate-500 hover:text-white hover:bg-slate-700 rounded transition-colors"
          >
            <ChevronRight size={13} />
          </button>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="text-center p-6 text-slate-600">
            <div className="text-4xl mb-3 opacity-30">⚙</div>
            <p className="text-sm font-medium">No agent selected</p>
            <p className="text-xs mt-1">Click an agent on the canvas to configure it</p>
          </div>
        </div>
      </aside>
    )
  }

  const save = () => {
    updateNodeData(selectedNode.id, localData)
    saveWorkflow()
  }

  const patch = (key, val) => setLocalData((d) => ({ ...d, [key]: val }))
  const patchProp = (key, val) =>
    setLocalData((d) => ({ ...d, properties: { ...d.properties, [key]: val } }))

  const nodeTools = tools.filter((t) => localData.tools?.includes(t.id))
  const toggleTool = (toolId) => {
    const current = localData.tools || []
    const next = current.includes(toolId)
      ? current.filter((id) => id !== toolId)
      : [...current, toolId]
    patch('tools', next)
    if (!next.includes(toolId) && expandedToolId === toolId) setExpandedToolId(null)
  }

  const patchToolConfig = (toolId, key, val) =>
    setLocalData((d) => ({
      ...d,
      toolConfigs: {
        ...(d.toolConfigs || {}),
        [toolId]: { ...(d.toolConfigs?.[toolId] || {}), [key]: val },
      },
    }))

  const resetToolConfig = (toolId) =>
    setLocalData((d) => {
      const configs = { ...(d.toolConfigs || {}) }
      delete configs[toolId]
      return { ...d, toolConfigs: configs }
    })

  const filteredTools = tools.filter((t) => {
    const q = toolSearch.toLowerCase()
    return !q || t.name.toLowerCase().includes(q) || t.description.toLowerCase().includes(q) || t.type.toLowerCase().includes(q)
  })

  return (
    <aside
      className="flex-shrink-0 bg-slate-900 border-l border-slate-800 flex flex-col overflow-hidden relative"
      style={{ width: panelWidth }}
    >
      {/* Resize handle */}
      <div
        onMouseDown={startResize}
        className="absolute left-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-indigo-500/60 transition-colors z-10"
      />
      {/* Header */}
      <div className="px-4 py-3 border-b border-slate-800 flex items-center justify-between">
        <div className="min-w-0">
          <p className="text-sm font-semibold text-slate-100 truncate">{localData.name}</p>
          <p className="text-[10px] text-slate-400 uppercase tracking-wide">
          {selectedNode.type === 'toolNode'
            ? (localData.toolType?.replace(/_/g, ' ') || 'Tool')
            : (localData.type?.replace(/_/g, ' ') || '')}
        </p>
        </div>
        <div className="flex items-center gap-1 flex-shrink-0">
          <button
            onClick={() => { deleteNode(selectedNode.id); setSelectedNode(null) }}
            className="p-1.5 text-slate-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors"
            title="Delete agent"
          >
            <Trash2 size={14} />
          </button>
          <button
            onClick={() => setSelectedNode(null)}
            className="p-1.5 text-slate-500 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
            title="Close panel"
          >
            <X size={14} />
          </button>
          <button
            onClick={onToggle}
            className="p-1.5 text-slate-500 hover:text-slate-200 hover:bg-slate-700 rounded transition-colors"
            title="Hide Properties"
          >
            <ChevronRight size={14} />
          </button>
        </div>
      </div>

      {/* Tabs — hide Tools/Invoke for Start/End/tool nodes */}
      <div className="flex border-b border-slate-800 bg-slate-900">
        {['properties', 'tools', 'invoke', 'execution']
          .filter((t) => {
            const isToolNode   = selectedNode.type === 'toolNode'
            const isLifecycle  = localData.type === 'start' || localData.type === 'end'
            if ((t === 'tools' || t === 'invoke') && (isToolNode || isLifecycle)) return false
            return true
          })
          .map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`flex-1 text-[11px] py-2 capitalize transition-colors ${
                tab === t
                  ? 'text-indigo-300 border-b-2 border-indigo-500 font-medium'
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              {t}
              {t === 'tools' && nodeTools.length > 0 && (
                <span className="ml-1 text-[9px] bg-indigo-600/40 text-indigo-300 rounded-full px-1.5 py-0.5">
                  {nodeTools.length}
                </span>
              )}
              {t === 'invoke' && ((localData.invoke?.input_parameters?.length || 0) + (localData.invoke?.output_parameters?.length || 0)) > 0 && (
                <span className="ml-1 text-[9px] bg-violet-600/40 text-violet-300 rounded-full px-1.5 py-0.5">
                  {(localData.invoke?.input_parameters?.length || 0) + (localData.invoke?.output_parameters?.length || 0)}
                </span>
              )}
            </button>
          ))}
      </div>

      {/* Panel body */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* ── Properties tab ── */}
        {tab === 'properties' && (
          <>
            <Section title="General">
              <Field label="Name">
                <input
                  type="text"
                  value={localData.name}
                  onChange={(e) => patch('name', e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </Field>
              {selectedNode.type === 'toolNode' ? (
                <Field label="Type">
                  <p className="text-xs text-slate-300 bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 capitalize">
                    {localData.toolType?.replace(/_/g, ' ') || 'Tool'}
                  </p>
                </Field>
              ) : (
                <Field label="Type">
                  <select
                    value={localData.type}
                    onChange={(e) => patch('type', e.target.value)}
                    className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {AGENT_TYPES.map((at) => (
                      <option key={at.value} value={at.value}>{at.label}</option>
                    ))}
                  </select>
                </Field>
              )}
              <Field label="Description">
                <textarea
                  value={localData.description || ''}
                  onChange={(e) => patch('description', e.target.value)}
                  rows={3}
                  className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
                />
              </Field>
            </Section>

            {selectedNode.type !== 'toolNode' && localData.type === 'start' && (
              <>
                <Section title="Workflow Configuration (Shared Read-Only)">
                  <p className="text-[10px] text-green-400/80 bg-green-900/20 border border-green-700/30 rounded px-2 py-1.5 leading-relaxed mb-2">
                    These values are broadcast to every agent and tool in this workflow as read-only configuration (e.g. environment, version, run parameters).
                  </p>
                  {Object.entries(localData.properties || {}).filter(([k]) => k !== 'triggers').map(([key, val]) => (
                    <Field key={key} label={key.replace(/_/g, ' ')}>
                      <PropValue propKey={key} val={val} onChange={v => patchProp(key, v)} />
                    </Field>
                  ))}
                </Section>

                <TriggersSection
                  triggers={localData.properties?.triggers || []}
                  workflowId={useStore.getState().workflowId}
                  onChange={(next) => patchProp('triggers', next)}
                />
              </>
            )}

            {selectedNode.type !== 'toolNode' && localData.type === 'end' && (
              <Section title="Output Collection (Write Access)">
                <p className="text-[10px] text-rose-400/80 bg-rose-900/20 border border-rose-700/30 rounded px-2 py-1.5 leading-relaxed mb-2">
                  All agents and tools in this workflow can write their final results here. These properties define the output schema for collected workflow data.
                </p>
                {Object.entries(localData.properties || {}).map(([key, val]) => (
                  <Field key={key} label={key.replace(/_/g, ' ')}>
                    <PropValue propKey={key} val={val} onChange={v => patchProp(key, v)} />
                  </Field>
                ))}
              </Section>
            )}

            {(selectedNode.type === 'toolNode' || (localData.type !== 'start' && localData.type !== 'end')) && Object.keys(localData.properties || {}).length > 0 && (
              <Section title="Configuration">
                {Object.entries(localData.properties).map(([key, val]) => (
                  <Field key={key} label={key.replace(/_/g, ' ')}>
                    <PropValue
                      propKey={key}
                      val={val}
                      onChange={v => patchProp(key, v)}
                    />
                  </Field>
                ))}
              </Section>
            )}
          </>
        )}

        {/* ── Tools tab ── */}
        {tab === 'tools' && (
          <Section title={`Tools (${nodeTools.length} assigned)`}>
            <div className="relative mb-1">
              <Search size={11} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              <input
                type="text"
                placeholder="Search tools…"
                value={toolSearch}
                onChange={(e) => setToolSearch(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded px-2.5 py-1.5 pl-7 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              {filteredTools.map((tool) => {
                const selected = localData.tools?.includes(tool.id)
                const isExpanded = expandedToolId === tool.id
                const overrides = localData.toolConfigs?.[tool.id] || {}
                const hasOverrides = Object.keys(overrides).length > 0

                return (
                  <div
                    key={tool.id}
                    className={`rounded-lg border transition-all ${
                      selected
                        ? 'bg-indigo-900/20 border-indigo-600/50'
                        : 'bg-slate-800/40 border-slate-700/40'
                    }`}
                  >
                    {/* Tool row */}
                    <div className="flex items-start gap-2 p-2">
                      <button
                        onClick={() => toggleTool(tool.id)}
                        className={`w-4 h-4 rounded border flex-shrink-0 mt-0.5 flex items-center justify-center transition-colors ${
                          selected ? 'bg-indigo-500 border-indigo-400' : 'border-slate-600 hover:border-slate-400'
                        }`}
                      >
                        {selected && <span className="text-[9px] text-white font-bold">✓</span>}
                      </button>

                      <div className="min-w-0 flex-1">
                        <p className={`text-xs font-medium leading-tight ${selected ? 'text-indigo-100' : 'text-slate-300'}`}>
                          {tool.name}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5 leading-tight line-clamp-2">{tool.description}</p>
                        <div className="flex items-center gap-1.5 mt-1">
                          <span className="text-[9px] text-slate-500 uppercase">{tool.type?.replace(/_/g, ' ')}</span>
                          {hasOverrides && (
                            <span className="text-[9px] text-indigo-400 bg-indigo-900/40 rounded px-1">configured</span>
                          )}
                        </div>
                      </div>

                      {selected && Object.keys(tool.properties || {}).length > 0 && (
                        <button
                          onClick={() => setExpandedToolId(isExpanded ? null : tool.id)}
                          title="Configure tool"
                          className={`p-1 rounded transition-colors flex-shrink-0 ${
                            isExpanded
                              ? 'text-indigo-300 bg-indigo-800/40'
                              : 'text-slate-500 hover:text-slate-300 hover:bg-slate-700/40'
                          }`}
                        >
                          <Settings2 size={12} />
                        </button>
                      )}
                    </div>

                    {selected && isExpanded && (
                      <div className="px-3 pb-3">
                        <ToolConfigEditor
                          tool={tool}
                          overrides={overrides}
                          onChange={(key, val) => patchToolConfig(tool.id, key, val)}
                        />
                        {hasOverrides && (
                          <button
                            onClick={() => resetToolConfig(tool.id)}
                            className="mt-2 text-[10px] text-slate-500 hover:text-red-400 transition-colors"
                          >
                            Reset overrides
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>

            {filteredTools.length === 0 && (
              <p className="text-[11px] text-slate-500 text-center py-2">No tools match your search.</p>
            )}
          </Section>
        )}

        {/* ── Invoke tab ── */}
        {tab === 'invoke' && (
          <InvokeTab
            localData={localData}
            onPatch={patch}
            dataModels={dataModels}
            currentAssociation={currentAssociation}
            nodes={nodes}
          />
        )}

        {/* ── Execution tab ── */}
        {tab === 'execution' && (
          localData.executionResult ? (
            <>
              <div className={`p-2.5 rounded-lg border text-xs font-medium text-center ${EXEC_STATUS_STYLES[localData.executionStatus] || EXEC_STATUS_STYLES.pending}`}>
                {localData.executionStatus?.toUpperCase()} — {localData.executionResult.duration_ms}ms
              </div>

              {Object.keys(localData.executionResult.invoke_inputs || {}).length > 0 && (
                <Section title="Invoke Inputs (Resolved)">
                  <pre className="text-[10px] text-violet-300 bg-violet-900/20 border border-violet-700/30 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(localData.executionResult.invoke_inputs, null, 2)}
                  </pre>
                </Section>
              )}

              <Section title="Input">
                <pre className="text-[10px] text-slate-300 bg-slate-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(localData.executionResult.input, null, 2)}
                </pre>
              </Section>

              <Section title="Output">
                <pre className="text-[10px] text-slate-300 bg-slate-800 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                  {JSON.stringify(localData.executionResult.output, null, 2)}
                </pre>
              </Section>

              {Object.keys(localData.executionResult.invoke_outputs || {}).length > 0 && (
                <Section title="Invoke Outputs (Captured)">
                  <pre className="text-[10px] text-violet-300 bg-violet-900/20 border border-violet-700/30 rounded p-2 overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(localData.executionResult.invoke_outputs, null, 2)}
                  </pre>
                </Section>
              )}

              <Section title="Logs">
                <div className="space-y-1">
                  {(localData.executionResult.logs || []).map((log, i) => (
                    <div key={i} className="flex gap-1.5 text-[10px]">
                      <span className="text-slate-600 flex-shrink-0">{String(i + 1).padStart(2, '0')}</span>
                      <span className={log.startsWith('ERROR') ? 'text-red-400' : 'text-slate-300'}>{log}</span>
                    </div>
                  ))}
                </div>
              </Section>
            </>
          ) : (
            <div className="text-center py-8 text-slate-600">
              <p className="text-sm">No execution results yet</p>
              <p className="text-xs mt-1">Run the workflow to see results here</p>
            </div>
          )
        )}
      </div>

      {/* Footer – save button (properties/tools/invoke tabs) */}
      {tab !== 'execution' && (
        <div className="p-3 border-t border-slate-800">
          <button
            onClick={save}
            className="w-full flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium py-2 rounded-lg transition-colors"
          >
            <Save size={14} />
            Apply Changes
          </button>
        </div>
      )}
    </aside>
  )
}
