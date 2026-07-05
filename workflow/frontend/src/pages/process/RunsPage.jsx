import { useState, useEffect, useRef } from 'react'
import {
  Activity, ArrowLeft, RefreshCw, Search, Bot, Wrench,
  ChevronDown, ChevronRight, Loader2, AlertCircle,
  CheckCircle2, XCircle, Clock, SkipForward, Square,
  User, CheckCircle, AlertTriangle, MessageSquare, Play,
  ClipboardCheck, Pencil, Sparkles,
  Download, Upload, FileText, Paperclip, X,
} from 'lucide-react'
import { getExecutions, getWorkflows, getWorkflow, runExecution } from '../../api/api'
import usePortalStore from '../../store/portalStore'

// ── Status helpers ─────────────────────────────────────────

const STATUS_STYLE = {
  completed: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  failed:    'bg-red-500/20    text-red-400    border border-red-500/30',
  pending:   'bg-amber-500/20  text-amber-400  border border-amber-500/30',
  running:   'bg-blue-500/20   text-blue-400   border border-blue-500/30',
  skipped:   'bg-slate-500/20  text-slate-400  border border-slate-500/30',
}

const STATUS_ICON = {
  completed: CheckCircle2,
  failed:    XCircle,
  pending:   Clock,
  running:   Loader2,
  skipped:   SkipForward,
}

function StatusBadge({ status }) {
  const Icon = STATUS_ICON[status] || Clock
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLE[status] || STATUS_STYLE.pending}`}>
      <Icon size={11} className={status === 'running' ? 'animate-spin' : ''} />
      {status}
    </span>
  )
}

// ── Formatting ─────────────────────────────────────────────

function fmtMs(ms) {
  if (ms == null) return '—'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  return `${Math.floor(ms / 60000)}m ${Math.round((ms % 60000) / 1000)}s`
}

function fmtDate(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString(undefined, {
      month: 'short', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit',
    })
  } catch { return iso }
}

function shortId(id) {
  return id ? `${id.slice(0, 8)}…` : '—'
}

// ── JSON display block ─────────────────────────────────────

function JsonBlock({ data }) {
  if (!data || Object.keys(data).length === 0) {
    return <p className="text-slate-500 text-xs italic">No data.</p>
  }
  return (
    <pre className="text-[11px] text-slate-300 font-mono whitespace-pre-wrap break-all bg-slate-950 rounded-lg p-3 overflow-y-auto max-h-52 leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

// ── Step detail (logs / input / output tabs) ───────────────

const STEP_TABS = [
  { id: 'logs',   label: 'Logs' },
  { id: 'input',  label: 'Inputs Resolved' },
  { id: 'output', label: 'Output Saved' },
  { id: 'model',  label: 'Model Data' },
]

function StepDetail({ step, dmInstance }) {
  const [tab, setTab] = useState('logs')

  const hasInvokeInputs  = step.invoke_inputs  && Object.keys(step.invoke_inputs).length  > 0
  const hasInvokeOutputs = step.invoke_outputs && Object.keys(step.invoke_outputs).length > 0
  const hasDmInstance    = dmInstance && Object.keys(dmInstance).length > 0

  return (
    <div className="mt-2 border-t border-slate-700/60 pt-3">
      <div className="flex gap-1 mb-3 flex-wrap">
        {STEP_TABS.map(({ id, label }) => {
          const badge =
            id === 'logs'   ? (step.logs?.length ?? 0) :
            id === 'input'  ? (hasInvokeInputs  ? Object.keys(step.invoke_inputs).length  : null) :
            id === 'output' ? (hasInvokeOutputs ? Object.keys(step.invoke_outputs).length : null) :
            id === 'model'  ? (hasDmInstance    ? Object.keys(dmInstance).length           : null) :
            null
          return (
            <button
              key={id}
              onClick={() => setTab(id)}
              className={`flex items-center gap-1.5 px-3 py-1 text-xs font-medium rounded transition-colors ${
                tab === id
                  ? 'bg-indigo-600 text-white'
                  : 'text-slate-400 hover:text-white bg-slate-700/50 hover:bg-slate-700'
              }`}
            >
              {label}
              {badge != null && (
                <span className={`text-[9px] rounded-full px-1.5 py-0.5 font-semibold ${
                  tab === id ? 'bg-white/20' : 'bg-slate-600 text-slate-300'
                }`}>
                  {badge}
                </span>
              )}
            </button>
          )
        })}
      </div>

      {tab === 'logs' && (
        <div className="space-y-1 max-h-52 overflow-y-auto pr-1">
          {(step.logs?.length ?? 0) === 0 ? (
            <p className="text-slate-500 text-xs italic">No logs.</p>
          ) : (
            step.logs.map((line, i) => (
              <div key={i} className="flex items-start gap-2">
                <span className="text-slate-600 font-mono text-[10px] shrink-0 w-5 text-right mt-0.5">{i + 1}</span>
                <span className={`font-mono text-[11px] leading-snug ${line.startsWith('ERROR') ? 'text-red-400' : 'text-slate-300'}`}>
                  {line}
                </span>
              </div>
            ))
          )}
        </div>
      )}

      {tab === 'input' && (
        hasInvokeInputs ? (
          <div>
            <p className="text-[10px] text-violet-400/70 uppercase tracking-wide mb-2">Resolved invoke parameters</p>
            <pre className="text-[11px] text-violet-200 font-mono whitespace-pre-wrap break-all bg-violet-950/40 border border-violet-700/30 rounded-lg p-3 overflow-y-auto max-h-52 leading-relaxed">
              {JSON.stringify(step.invoke_inputs, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-slate-500 text-xs italic">No invoke inputs for this step.</p>
        )
      )}

      {tab === 'output' && (
        hasInvokeOutputs ? (
          <div>
            <p className="text-[10px] text-violet-400/70 uppercase tracking-wide mb-2">Captured output parameters</p>
            <pre className="text-[11px] text-violet-200 font-mono whitespace-pre-wrap break-all bg-violet-950/40 border border-violet-700/30 rounded-lg p-3 overflow-y-auto max-h-52 leading-relaxed">
              {JSON.stringify(step.invoke_outputs, null, 2)}
            </pre>
          </div>
        ) : (
          <p className="text-slate-500 text-xs italic">No invoke outputs captured for this step.</p>
        )
      )}

      {tab === 'model' && (
        hasDmInstance ? (
          <div>
            <p className="text-[10px] text-emerald-400/70 uppercase tracking-wide mb-2">Data model instance</p>
            <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
              {Object.entries(dmInstance).map(([entity, fields]) => (
                <div key={entity} className="bg-emerald-950/30 border border-emerald-700/25 rounded-lg p-2.5">
                  <p className="text-[10px] font-semibold text-emerald-400 mb-1.5">{entity}</p>
                  <div className="space-y-0.5">
                    {typeof fields === 'object' && fields !== null
                      ? Object.entries(fields).map(([field, val]) => (
                          <div key={field} className="flex items-baseline gap-2 text-[11px]">
                            <span className="text-slate-400 shrink-0 w-28 truncate">{field}</span>
                            <span className="text-emerald-200 font-mono truncate">
                              {val === null || val === undefined || val === '' ? (
                                <span className="text-slate-600 italic">—</span>
                              ) : String(val)}
                            </span>
                          </div>
                        ))
                      : <span className="text-emerald-200 font-mono text-[11px]">{String(fields)}</span>
                    }
                  </div>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-slate-500 text-xs italic">No data model linked to this workflow.</p>
        )
      )}
    </div>
  )
}

// ── Single step card ───────────────────────────────────────

function StepCard({ step, index, dmInstance }) {
  const [open, setOpen] = useState(false)
  const isTool = step.node_kind === 'tool'
  const Icon = isTool ? Wrench : Bot

  return (
    <div className={`bg-slate-900 border rounded-lg overflow-hidden ${
      step.status === 'failed' ? 'border-red-500/30' : 'border-slate-700'
    }`}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-800/60 transition-colors text-left"
      >
        <span className="text-slate-600 text-[11px] font-mono w-5 shrink-0 text-right">{index + 1}</span>
        <Icon size={14} className={`shrink-0 ${isTool ? 'text-cyan-400' : 'text-indigo-400'}`} />
        <span className="flex-1 text-sm font-medium text-white truncate">{step.agent_name}</span>
        <span className="text-[11px] text-slate-500 font-mono shrink-0">{fmtMs(step.duration_ms)}</span>
        <StatusBadge status={step.status} />
        {open
          ? <ChevronDown size={13} className="text-slate-500 shrink-0" />
          : <ChevronRight size={13} className="text-slate-500 shrink-0" />
        }
      </button>

      {open && (
        <div className="px-4 pb-4">
          <StepDetail step={step} dmInstance={dmInstance} />
        </div>
      )}
    </div>
  )
}

// ── HITL / Human-Review constants ──────────────────────────

const JUDGMENT_ICONS = {
  'Approve':           <CheckCircle   size={15} className="text-green-400" />,
  'Reject':            <XCircle       size={15} className="text-red-400" />,
  'Escalate':          <AlertTriangle size={15} className="text-amber-400" />,
  'Request More Info': <MessageSquare size={15} className="text-blue-400" />,
  'Correct Output':    <Pencil        size={15} className="text-indigo-400" />,
  'Override Decision': <RefreshCw     size={15} className="text-fuchsia-400" />,
  'Provide Feedback':  <MessageSquare size={15} className="text-cyan-400" />,
}

const JUDGMENT_STYLES = {
  'Approve':           'border-green-600/50 bg-green-900/20 text-green-200',
  'Reject':            'border-red-600/50 bg-red-900/20 text-red-200',
  'Escalate':          'border-amber-600/50 bg-amber-900/20 text-amber-200',
  'Request More Info': 'border-blue-600/50 bg-blue-900/20 text-blue-200',
  'Correct Output':    'border-indigo-600/50 bg-indigo-900/20 text-indigo-200',
  'Override Decision': 'border-fuchsia-600/50 bg-fuchsia-900/20 text-fuchsia-200',
  'Provide Feedback':  'border-cyan-600/50 bg-cyan-900/20 text-cyan-200',
}

// HITL = active collaboration inside the loop; Review = validation checkpoint after automation.
const MODE_META = {
  hitl: {
    title: 'Human-in-the-Loop',
    subtitle: 'Active collaboration — approve, correct, override, or feed back so the model learns.',
    icon: User,
    border: 'border-amber-600/40',
    headerBg: 'bg-amber-900/10',
    chipCls: 'text-amber-500 bg-amber-900/30 border-amber-700/40',
    iconWrap: 'bg-amber-600/30 border-amber-600/50',
    iconCls: 'text-amber-300',
    submitCls: 'bg-amber-600 hover:bg-amber-500',
    focusCls: 'focus:border-amber-500',
  },
  review: {
    title: 'Human Review',
    subtitle: 'Validation checkpoint after automation — verify the AI output and approve or reject.',
    icon: ClipboardCheck,
    border: 'border-sky-600/40',
    headerBg: 'bg-sky-900/10',
    chipCls: 'text-sky-400 bg-sky-900/30 border-sky-700/40',
    iconWrap: 'bg-sky-600/30 border-sky-600/50',
    iconCls: 'text-sky-300',
    submitCls: 'bg-sky-600 hover:bg-sky-500',
    focusCls: 'focus:border-sky-500',
  },
}

const isMultiline = (key) =>
  ['notes', 'comment', 'feedback', 'summary', 'correct', 'rationale'].some(t =>
    key.toLowerCase().includes(t)
  )

// Trigger a browser download for a file descriptor ({ name, type, content }).
const downloadStepFile = (file) => {
  const blob = new Blob([file.content ?? ''], { type: file.type || 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = file.name || 'download'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ── HITL / Human-Review modal (self-contained, no store dep) ──

function LiveHumanInputModal({ humanInput, onAbort }) {
  const { step, resume } = humanInput
  const [judgment, setJudgment] = useState(null)
  const [inputs, setInputs]     = useState({})
  const [uploads, setUploads]   = useState([])

  useEffect(() => {
    setJudgment(null)
    setUploads([])
    setInputs(
      Object.fromEntries(
        Object.entries(step.input_fields || {}).map(([k, v]) => [k, String(v)])
      )
    )
  }, [humanInput])

  const options       = step.judgment_options || []
  const meta          = MODE_META[step.review_mode] || MODE_META.hitl
  const HeaderIcon    = meta.icon
  const aiOutput      = step.ai_output || {}
  const downloadFiles = step.download_files || []
  const patchInput    = (k, v) => setInputs(p => ({ ...p, [k]: v }))

  const handleUpload = (e) => {
    const picked = Array.from(e.target.files || []).map(f => ({ name: f.name, size: f.size }))
    setUploads(prev => [...prev, ...picked])
    e.target.value = ''
  }

  const handleResume = () => {
    if (!judgment) return
    const merged = uploads.length
      ? { ...inputs, uploaded_files: uploads.map(u => u.name).join(', ') }
      : inputs
    resume({ judgment, inputs: merged })
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/70" />

      <div className={`relative bg-slate-900 border ${meta.border} rounded-2xl shadow-2xl w-[480px] max-h-[88vh] flex flex-col overflow-hidden`}>
        {/* Header */}
        <div className={`flex items-center gap-3 px-5 py-4 border-b border-slate-800 ${meta.headerBg}`}>
          <div className={`w-8 h-8 rounded-full border flex items-center justify-center flex-shrink-0 ${meta.iconWrap}`}>
            <HeaderIcon size={15} className={meta.iconCls} />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-100">{meta.title}</p>
            <p className={`text-[11px] truncate ${meta.iconCls}`}>{step.agent_name}</p>
          </div>
          <span className={`ml-auto text-[9px] uppercase tracking-widest border px-2 py-0.5 rounded-full animate-pulse ${meta.chipCls}`}>
            Awaiting input
          </span>
        </div>

        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Mode explanation */}
          <p className="text-[11px] text-slate-400 leading-snug">{meta.subtitle}</p>

          {/* AI-produced output */}
          {Object.keys(aiOutput).length > 0 && (
            <div className="bg-slate-800/60 rounded-lg p-3 border border-slate-700/60">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Sparkles size={11} className="text-indigo-400" />
                AI Output
              </p>
              <div className="space-y-1">
                {Object.entries(aiOutput).map(([k, v]) => (
                  <div key={k} className="flex justify-between gap-3 text-xs">
                    <span className="text-slate-400 capitalize flex-shrink-0">{k.replace(/_/g, ' ')}</span>
                    <span className="text-slate-200 font-medium text-right">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Files: download artifacts (both modes) + upload (HITL only) */}
          {(downloadFiles.length > 0 || step.allow_upload) && (
            <div>
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2 flex items-center gap-1.5">
                <Paperclip size={11} className={meta.iconCls} />
                Files
              </p>

              {downloadFiles.length > 0 && (
                <div className="space-y-1.5">
                  {downloadFiles.map((f, idx) => (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => downloadStepFile(f)}
                      className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-700/60 bg-slate-800/50 hover:border-slate-600 hover:bg-slate-800 transition-colors text-left"
                    >
                      <FileText size={14} className="text-slate-400 flex-shrink-0" />
                      <span className="text-xs text-slate-200 truncate flex-1">{f.name}</span>
                      {f.size_kb != null && (
                        <span className="text-[10px] text-slate-500">{f.size_kb} KB</span>
                      )}
                      <Download size={13} className={meta.iconCls} />
                    </button>
                  ))}
                </div>
              )}

              {step.allow_upload && (
                <div className={downloadFiles.length > 0 ? 'mt-2' : ''}>
                  <label className="flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border border-dashed border-slate-600 hover:border-slate-500 bg-slate-800/30 cursor-pointer transition-colors">
                    <Upload size={14} className={meta.iconCls} />
                    <span className="text-xs text-slate-300">Upload file(s)</span>
                    <input type="file" multiple className="hidden" onChange={handleUpload} />
                  </label>
                  {uploads.length > 0 && (
                    <div className="mt-1.5 space-y-1">
                      {uploads.map((u, idx) => (
                        <div key={idx} className="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-slate-800/60 border border-slate-700/50">
                          <FileText size={12} className="text-emerald-400 flex-shrink-0" />
                          <span className="text-[11px] text-slate-200 truncate flex-1">{u.name}</span>
                          <button
                            type="button"
                            onClick={() => setUploads(prev => prev.filter((_, i) => i !== idx))}
                            className="text-slate-500 hover:text-red-400 transition-colors"
                          >
                            <X size={12} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Execution context */}
          {Object.keys(step.input || {}).length > 0 && (
            <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">Execution Context</p>
              <div className="space-y-1">
                {Object.entries(step.input).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-xs">
                    <span className="text-slate-400 capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="text-slate-200 font-medium">{String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Input fields */}
          {Object.keys(inputs).length > 0 && (
            <div>
              <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">
                {step.review_mode === 'review' ? 'Validation Inputs' : 'Collaboration Inputs'}
              </p>
              <div className="space-y-2.5">
                {Object.entries(inputs).map(([key, val]) => (
                  <div key={key}>
                    <label className="block text-[10px] text-slate-400 mb-0.5 capitalize">
                      {key.replace(/_/g, ' ')}
                    </label>
                    {isMultiline(key) ? (
                      <textarea
                        rows={2}
                        value={val}
                        onChange={e => patchInput(key, e.target.value)}
                        className={`w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none ${meta.focusCls} transition-colors resize-none`}
                        placeholder={`Enter ${key.replace(/_/g, ' ')}…`}
                      />
                    ) : (
                      <input
                        type="text"
                        value={val}
                        onChange={e => patchInput(key, e.target.value)}
                        className={`w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none ${meta.focusCls} transition-colors`}
                      />
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Judgment options */}
          <div>
            <p className="text-[10px] text-slate-500 uppercase tracking-wide mb-2">
              {step.review_mode === 'review' ? 'Validation Decision' : 'Select Action'} <span className="text-red-400">*</span>
            </p>
            <div className="grid grid-cols-2 gap-2">
              {options.map(opt => {
                const isSelected = judgment === opt
                const style = JUDGMENT_STYLES[opt] || 'border-indigo-600/50 bg-indigo-900/20 text-indigo-200'
                return (
                  <button
                    key={opt}
                    onClick={() => setJudgment(opt)}
                    className={`flex items-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-medium transition-all ${
                      isSelected
                        ? `${style} ring-2 ring-offset-1 ring-offset-slate-900 ring-current scale-[1.02]`
                        : 'border-slate-700/50 text-slate-400 hover:border-slate-600 hover:text-slate-200'
                    }`}
                  >
                    {JUDGMENT_ICONS[opt] || <CheckCircle size={14} />}
                    {opt}
                  </button>
                )
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-5 py-3 border-t border-slate-800 bg-slate-900/80">
          <button
            onClick={onAbort}
            className="text-xs text-slate-500 hover:text-red-400 transition-colors"
          >
            Abort execution
          </button>
          <button
            onClick={handleResume}
            disabled={!judgment}
            className={`px-4 py-1.5 text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-colors ${meta.submitCls}`}
          >
            Submit &amp; Resume
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Live run view ──────────────────────────────────────────

function LiveRunView({ liveRun, liveSteps, currentStep, humanInput, onStop, onBack, onViewHistory, dmInstance }) {
  const isRunning      = liveRun.status === 'running'
  const displaySteps   = currentStep ? [...liveSteps, currentStep] : liveSteps
  const completedCount = displaySteps.filter(s => s.status === 'completed').length
  const failedCount    = displaySteps.filter(s => s.status === 'failed').length
  const skippedCount   = displaySteps.filter(s => s.status === 'skipped').length

  return (
    <div>
      {/* HITL modal */}
      {humanInput && (
        <LiveHumanInputModal humanInput={humanInput} onAbort={onStop} />
      )}

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-2 flex-wrap">
          <button
            onClick={onBack}
            className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={15} />
            Runs
          </button>
          <span className="text-slate-600 text-sm">/</span>
          <span className="text-white text-sm font-medium truncate max-w-xs">{liveRun.workflowName}</span>
          <StatusBadge status={liveRun.status} />
        </div>

        <div className="flex items-center gap-2">
          {isRunning ? (
            <button
              onClick={onStop}
              className="flex items-center gap-1.5 text-xs font-medium text-red-400 hover:text-red-300 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 px-3 py-1.5 rounded-lg transition-colors"
            >
              <Square size={11} />
              Stop
            </button>
          ) : (
            <button
              onClick={onViewHistory}
              className="flex items-center gap-1.5 text-xs font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-500/10 hover:bg-indigo-500/20 border border-indigo-500/20 px-3 py-1.5 rounded-lg transition-colors"
            >
              View in History →
            </button>
          )}
        </div>
      </div>

      {/* Summary card */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 mb-6">
        <div className="flex flex-wrap gap-6 items-start justify-between">
          <div>
            <h2 className="text-lg font-semibold text-white mb-1">{liveRun.workflowName}</h2>
            {liveRun.runId && (
              <p className="text-slate-500 text-xs font-mono">Run ID: {liveRun.runId}</p>
            )}
          </div>

          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <p className="text-slate-500 text-xs mb-0.5">Started</p>
              <p className="text-slate-200 text-sm">{fmtDate(liveRun.startedAt)}</p>
            </div>
            {liveRun.totalDurationMs != null && (
              <div>
                <p className="text-slate-500 text-xs mb-0.5">Duration</p>
                <p className="text-slate-200 font-mono text-sm">{fmtMs(liveRun.totalDurationMs)}</p>
              </div>
            )}
            <div>
              <p className="text-slate-500 text-xs mb-0.5">Steps</p>
              <p className="text-slate-200 text-sm">
                {displaySteps.length} shown
                {completedCount > 0 && <span className="text-emerald-400 ml-1.5">· {completedCount} done</span>}
                {failedCount    > 0 && <span className="text-red-400 ml-1.5">· {failedCount} failed</span>}
                {skippedCount   > 0 && <span className="text-slate-500 ml-1.5">· {skippedCount} skipped</span>}
              </p>
            </div>
          </div>
        </div>

        {isRunning && (
          <div className="mt-4 pt-4 border-t border-slate-700 flex items-center gap-2 text-sm">
            <Loader2 size={14} className="animate-spin text-blue-400" />
            <span className="text-slate-400">
              {humanInput ? 'Awaiting human review…' : 'Executing…'}
            </span>
          </div>
        )}
      </div>

      {/* Live steps */}
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Live Execution
      </h3>
      <div className="space-y-2">
        {displaySteps.length === 0 ? (
          <div className="flex items-center gap-2 text-slate-400 py-6">
            <Loader2 size={16} className="animate-spin" />
            <span className="text-sm">Starting execution…</span>
          </div>
        ) : (
          displaySteps.map((step, i) => (
            <StepCard key={i} step={step} index={i} dmInstance={dmInstance || {}} />
          ))
        )}
      </div>
    </div>
  )
}

// ── Run detail view ────────────────────────────────────────

function RunDetail({ run, workflowName, onBack }) {
  const failedCount  = run.steps.filter(s => s.status === 'failed').length
  const skippedCount = run.steps.filter(s => s.status === 'skipped').length
  const toolSteps    = run.steps.filter(s => s.node_kind === 'tool').length
  const agentSteps   = run.steps.filter(s => s.node_kind !== 'tool').length

  return (
    <div>
      {/* Breadcrumb */}
      <div className="flex items-center gap-2 mb-6">
        <button
          onClick={onBack}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-white transition-colors"
        >
          <ArrowLeft size={15} />
          Runs
        </button>
        <span className="text-slate-600 text-sm">/</span>
        <span className="text-white text-sm font-medium truncate">{workflowName}</span>
      </div>

      {/* Summary card */}
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 mb-6">
        <div className="flex flex-wrap gap-6 items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1.5">
              <h2 className="text-lg font-semibold text-white">{workflowName}</h2>
              <StatusBadge status={run.status} />
            </div>
            <p className="text-slate-500 text-xs font-mono">Run ID: {run.id}</p>
          </div>

          <div className="flex flex-wrap gap-6 text-sm">
            <div>
              <p className="text-slate-500 text-xs mb-0.5">Started</p>
              <p className="text-slate-200 text-sm">{fmtDate(run.started_at)}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs mb-0.5">Duration</p>
              <p className="text-slate-200 font-mono text-sm">{fmtMs(run.total_duration_ms)}</p>
            </div>
            <div>
              <p className="text-slate-500 text-xs mb-0.5">Steps</p>
              <p className="text-slate-200 text-sm">
                {run.steps.length} total
                {agentSteps > 0  && <span className="text-indigo-400 ml-1.5">· {agentSteps} agent{agentSteps !== 1 ? 's' : ''}</span>}
                {toolSteps > 0   && <span className="text-cyan-400 ml-1.5">· {toolSteps} tool{toolSteps !== 1 ? 's' : ''}</span>}
                {failedCount > 0 && <span className="text-red-400 ml-1.5">· {failedCount} failed</span>}
                {skippedCount > 0 && <span className="text-slate-500 ml-1.5">· {skippedCount} skipped</span>}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Steps */}
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
        Execution Steps
      </h3>
      <div className="space-y-2">
        {run.steps.length === 0 ? (
          <p className="text-slate-500 text-sm py-8 text-center">No steps recorded.</p>
        ) : (
          run.steps.map((step, i) => (
            <StepCard key={step.node_id || i} step={step} index={i} dmInstance={run.data_model_instance || {}} />
          ))
        )}
      </div>
    </div>
  )
}

// ── Runs list view ─────────────────────────────────────────

const STATUS_TABS = ['all', 'completed', 'failed', 'pending']

function RunsList({ runs, workflowMap, loading, error, search, setSearch, statusFilter, setStatusFilter, onRefresh, onSelect }) {
  const filtered = runs.filter(r => {
    const name = (workflowMap[r.workflow_id] || r.workflow_id).toLowerCase()
    const matchSearch  = !search || name.includes(search.toLowerCase()) || r.id.includes(search.toLowerCase())
    const matchStatus  = statusFilter === 'all' || r.status === statusFilter
    return matchSearch && matchStatus
  })

  const counts = STATUS_TABS.slice(1).reduce((acc, s) => {
    acc[s] = runs.filter(r => r.status === s).length
    return acc
  }, {})

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Workflow Runs</h1>
          <p className="text-slate-400 text-sm mt-1">Execution history across all workflows.</p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-2 bg-slate-700 hover:bg-slate-600 text-white text-sm font-medium px-3 py-2 rounded-lg transition-colors disabled:opacity-50"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative min-w-[220px]">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by workflow or run ID…"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg pl-9 pr-4 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
        <div className="flex gap-1 bg-slate-800 border border-slate-700 rounded-lg p-1">
          {STATUS_TABS.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-1 rounded text-xs font-medium capitalize transition-colors flex items-center gap-1.5 ${
                statusFilter === s ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              {s === 'all' ? 'All' : s}
              {s !== 'all' && counts[s] > 0 && (
                <span className="bg-slate-600 text-slate-300 rounded-full px-1.5 text-[10px]">{counts[s]}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading runs…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10">
          <AlertCircle size={18} /> {error}
        </div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Workflow</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden sm:table-cell">Run ID</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Status</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Started</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Duration</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Steps</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-14">
                    <Activity size={32} className="mx-auto mb-2 opacity-30" />
                    {runs.length === 0
                      ? 'No runs yet. Use the Run button on a workflow to start.'
                      : 'No runs match your filters.'
                    }
                  </td>
                </tr>
              ) : (
                filtered.map(run => {
                  const wfName = workflowMap[run.workflow_id] || `Workflow ${shortId(run.workflow_id)}`
                  const failedSteps = run.steps.filter(s => s.status === 'failed').length
                  return (
                    <tr
                      key={run.id}
                      onClick={() => onSelect(run)}
                      className="hover:bg-slate-700/50 transition-colors cursor-pointer"
                    >
                      <td className="px-4 py-3 font-medium text-white">{wfName}</td>
                      <td className="px-4 py-3 text-slate-400 font-mono text-xs hidden sm:table-cell">{shortId(run.id)}</td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2 flex-wrap">
                          <StatusBadge status={run.status} />
                          {failedSteps > 0 && (
                            <span className="text-[10px] text-red-400">
                              {failedSteps} step{failedSteps > 1 ? 's' : ''} failed
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden md:table-cell">{fmtDate(run.started_at)}</td>
                      <td className="px-4 py-3 text-slate-300 font-mono text-xs hidden lg:table-cell">{fmtMs(run.total_duration_ms)}</td>
                      <td className="px-4 py-3 text-slate-400 text-xs hidden lg:table-cell">{run.steps.length}</td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={e => { e.stopPropagation(); onSelect(run) }}
                          className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
                        >
                          View →
                        </button>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────

export default function RunsPage() {
  const [view, setView]               = useState('list')   // 'list' | 'detail' | 'live'
  const [selectedRun, setSelectedRun] = useState(null)
  const [runs, setRuns]               = useState([])
  const [workflowMap, setWorkflowMap] = useState({})
  const [loading, setLoading]         = useState(true)
  const [error, setError]             = useState(null)
  const [search, setSearch]           = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  // Live execution state
  const [liveRun, setLiveRun]         = useState(null)   // { workflowId, workflowName, runId, status, startedAt, totalDurationMs }
  const [liveSteps, setLiveSteps]     = useState([])     // final-status steps (completed/failed/skipped)
  const [currentStep, setCurrentStep] = useState(null)   // single step currently animating as 'running'
  const [humanInput, setHumanInput]   = useState(null)   // { step, stepIndex, resume } | null
  const abortRef                      = useRef(false)
  const runAttemptRef                 = useRef(0)   // guards against Strict Mode double-invocation

  const { activeRunWorkflow, clearActiveRun } = usePortalStore()

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (activeRunWorkflow) {
      const { id, name } = activeRunWorkflow
      clearActiveRun()
      startLiveRun(id, name)
    }
  }, [activeRunWorkflow])

  // Stop animation on unmount
  useEffect(() => () => { abortRef.current = true }, [])

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const [runsData, wfData] = await Promise.all([getExecutions(), getWorkflows()])
      setRuns([...runsData].sort((a, b) => new Date(b.started_at) - new Date(a.started_at)))
      const map = {}
      wfData.forEach(w => { map[w.id] = w.name })
      setWorkflowMap(map)
    } catch {
      setError('Failed to load runs.')
    } finally {
      setLoading(false)
    }
  }

  async function startLiveRun(workflowId, workflowName) {
    const attempt = ++runAttemptRef.current
    abortRef.current = false
    setLiveRun({ workflowId, workflowName, runId: null, status: 'running', startedAt: new Date().toISOString(), totalDurationMs: null })
    setLiveSteps([])
    setCurrentStep(null)
    setHumanInput(null)
    setView('live')

    try {
      const result = await runExecution(workflowId)
      if (attempt !== runAttemptRef.current) return  // stale: a second startLiveRun already took over
      setLiveRun(prev => prev ? { ...prev, runId: result.id } : null)

      // The backend returns a step for every node; load the graph so we can
      // walk only the path taken — branching (non-parallel) agents follow a
      // single output flow rather than executing every branch.
      const wf = await getWorkflow(workflowId).catch(() => null)
      const wfNodes = wf?.nodes || []
      const wfEdges = wf?.edges || []
      const nodeById = Object.fromEntries(wfNodes.map(n => [n.id, n]))
      const stepMap = {}
      result.steps.forEach(s => { stepMap[s.node_id] = s })
      const outgoingEdges = id => wfEdges.filter(e => e.source === id)
      const isParallel = id => (nodeById[id]?.data?.type) === 'parallel'

      const pickBranch = (decision, candidates) => {
        const norm = v => (v ?? '').toString().trim().toLowerCase()
        const d = norm(decision)
        if (d) {
          const exact = candidates.find(e => norm(e.label) === d)
          if (exact) return exact
        }
        const POSITIVE = ['approve', 'accept', 'yes', 'true', 'success', 'pass', 'continue', 'proceed', 'ok']
        const NEGATIVE = ['reject', 'deny', 'no', 'false', 'fail', 'failed', 'decline', 'stop']
        if (POSITIVE.includes(d)) {
          const m = candidates.find(e => POSITIVE.includes(norm(e.label)))
          if (m) return m
        }
        if (NEGATIVE.includes(d)) {
          const m = candidates.find(e => NEGATIVE.includes(norm(e.label)))
          if (m) return m
        }
        if (d) {
          const partial = candidates.find(e => norm(e.label) && (norm(e.label).includes(d) || d.includes(norm(e.label))))
          if (partial) return partial
        }
        return candidates[0]
      }

      const startNode = wfNodes.find(n => n.data?.type === 'start')
      const frontier = [startNode?.id || result.steps[0]?.node_id].filter(Boolean)
      const visited = new Set()

      await new Promise(resolve => {
        const finishRun = (status) => {
          setCurrentStep(null)
          setLiveRun(prev => prev
            ? { ...prev, status, totalDurationMs: result.total_duration_ms, dataModelInstance: result.data_model_instance || {} }
            : null
          )
          load()
          resolve()
        }

        const visitNext = () => {
          if (abortRef.current) { resolve(); return }
          while (frontier.length && visited.has(frontier[0])) frontier.shift()
          if (frontier.length === 0) { finishRun('completed'); return }

          const nodeId = frontier.shift()
          visited.add(nodeId)
          const step = stepMap[nodeId]
          if (!step) { visitNext(); return }

          // Show step as "running" — it's the only live step at any moment
          setCurrentStep({ ...step, status: 'running' })

          const advance = (completedStep, decision) => {
            setLiveSteps(prev => [...prev, completedStep])
            setCurrentStep(null)

            if (completedStep.status === 'failed') { finishRun('failed'); return }

            const outs = outgoingEdges(nodeId)
            let nextIds = []
            if (outs.length <= 1) {
              nextIds = outs.map(e => e.target)
            } else if (isParallel(nodeId)) {
              nextIds = outs.map(e => e.target)
            } else {
              const picked = pickBranch(decision, outs)
              nextIds = picked ? [picked.target] : []
            }
            nextIds.forEach(id => { if (!visited.has(id)) frontier.push(id) })
            setTimeout(visitNext, 700)
          }

          if (step.requires_human_input) {
            setHumanInput({
              step,
              resume: (humanResponse) => {
                const completedStep = {
                  ...step,
                  status: 'completed',
                  output: {
                    judgment: humanResponse.judgment,
                    ...Object.fromEntries(
                      Object.entries(humanResponse.inputs).filter(([, v]) => v !== '')
                    ),
                  },
                  logs: [
                    ...(step.logs || []),
                    `Judgment: ${humanResponse.judgment}`,
                    'Human review completed.',
                  ],
                }
                setHumanInput(null)
                advance(completedStep, humanResponse.judgment)
              },
            })
            return // paused — resumes via resume()
          }

          // After delay, commit step to final-status list and start next
          setTimeout(() => {
            if (abortRef.current) { resolve(); return }
            const decision = step.output?.branch ?? step.output?.decision ?? step.output?.judgment ?? null
            advance({ ...step }, decision)
          }, 1400)
        }

        visitNext()
      })
    } catch {
      setCurrentStep(null)
      setLiveRun(prev => prev ? { ...prev, status: 'failed' } : null)
    }
  }

  function stopLiveRun() {
    abortRef.current = true
    setCurrentStep(null)
    setHumanInput(null)
    setLiveRun(prev => prev ? { ...prev, status: 'failed' } : null)
  }

  function selectRun(run) {
    setSelectedRun(run)
    setView('detail')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      {view === 'live' && liveRun ? (
        <LiveRunView
          liveRun={liveRun}
          liveSteps={liveSteps}
          currentStep={currentStep}
          humanInput={humanInput}
          onStop={stopLiveRun}
          onBack={() => { abortRef.current = true; setCurrentStep(null); setHumanInput(null); setView('list') }}
          onViewHistory={() => setView('list')}
          dmInstance={liveRun.dataModelInstance || {}}
        />
      ) : view === 'detail' && selectedRun ? (
        <RunDetail
          run={selectedRun}
          workflowName={workflowMap[selectedRun.workflow_id] || `Workflow ${shortId(selectedRun.workflow_id)}`}
          onBack={() => setView('list')}
        />
      ) : (
        <RunsList
          runs={runs}
          workflowMap={workflowMap}
          loading={loading}
          error={error}
          search={search}
          setSearch={setSearch}
          statusFilter={statusFilter}
          setStatusFilter={setStatusFilter}
          onRefresh={load}
          onSelect={selectRun}
        />
      )}
    </div>
  )
}
