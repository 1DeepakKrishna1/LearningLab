import { useState, useEffect } from 'react'
import {
  User, ClipboardCheck, CheckCircle, XCircle, AlertTriangle,
  MessageSquare, Pencil, RefreshCw, Sparkles,
  Download, Upload, FileText, Paperclip, X,
} from 'lucide-react'
import useStore from '../store/workflowStore'

const JUDGMENT_ICONS = {
  'Approve':            <CheckCircle   size={15} className="text-green-400" />,
  'Reject':             <XCircle       size={15} className="text-red-400" />,
  'Escalate':           <AlertTriangle size={15} className="text-amber-400" />,
  'Request More Info':  <MessageSquare size={15} className="text-blue-400" />,
  'Correct Output':     <Pencil        size={15} className="text-indigo-400" />,
  'Override Decision':  <RefreshCw     size={15} className="text-fuchsia-400" />,
  'Provide Feedback':   <MessageSquare size={15} className="text-cyan-400" />,
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

const DEFAULT_STYLE = 'border-indigo-600/50 bg-indigo-900/20 text-indigo-200'

// Mode-specific framing — mirrors HITL (active collaboration in-loop) vs
// Human Review (validation checkpoint after automation).
const MODE_META = {
  hitl: {
    title: 'Human-in-the-Loop',
    subtitle: 'Active collaboration — approve, correct, override, or feed back so the model learns.',
    icon: User,
    accent: 'amber',
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
    accent: 'sky',
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
  ['notes', 'comment', 'feedback', 'summary', 'correct', 'rationale'].some((t) =>
    key.toLowerCase().includes(t)
  )

// Trigger a browser download for a file descriptor ({ name, type, content }).
export const downloadStepFile = (file) => {
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

export default function HumanInputModal() {
  const { humanInputPending, submitHumanInput, stopExecution } = useStore()

  const [judgment, setJudgment] = useState(null)
  const [inputs, setInputs]     = useState({})
  const [uploads, setUploads]   = useState([])

  // Reset form whenever a new step needs human input
  useEffect(() => {
    if (humanInputPending) {
      setJudgment(null)
      setUploads([])
      setInputs(
        Object.fromEntries(
          Object.entries(humanInputPending.step.input_fields || {}).map(([k, v]) => [k, String(v)])
        )
      )
    }
  }, [humanInputPending])

  if (!humanInputPending) return null

  const { step } = humanInputPending
  const options  = step.judgment_options || []
  const meta     = MODE_META[step.review_mode] || MODE_META.hitl
  const HeaderIcon = meta.icon
  const aiOutput = step.ai_output || {}
  const downloadFiles = step.download_files || []

  const handleSubmit = () => {
    if (!judgment) return
    const merged = uploads.length
      ? { ...inputs, uploaded_files: uploads.map((u) => u.name).join(', ') }
      : inputs
    submitHumanInput(judgment, merged)
  }

  const handleUpload = (e) => {
    const picked = Array.from(e.target.files || []).map((f) => ({ name: f.name, size: f.size }))
    setUploads((prev) => [...prev, ...picked])
    e.target.value = '' // allow re-selecting the same file
  }

  const patchInput = (key, val) => setInputs((prev) => ({ ...prev, [key]: val }))

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
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

          {/* AI-produced output the human is collaborating on / validating */}
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
                            onClick={() => setUploads((prev) => prev.filter((_, i) => i !== idx))}
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

          {/* Context from execution input */}
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
                        onChange={(e) => patchInput(key, e.target.value)}
                        className={`w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none ${meta.focusCls} transition-colors resize-none`}
                        placeholder={`Enter ${key.replace(/_/g, ' ')}…`}
                      />
                    ) : (
                      <input
                        type="text"
                        value={val}
                        onChange={(e) => patchInput(key, e.target.value)}
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
              {options.map((opt) => {
                const isSelected = judgment === opt
                const style = JUDGMENT_STYLES[opt] || DEFAULT_STYLE
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
            onClick={stopExecution}
            className="text-xs text-slate-500 hover:text-red-400 transition-colors"
          >
            Abort execution
          </button>
          <div className="flex items-center gap-2">
            <button
              onClick={handleSubmit}
              disabled={!judgment}
              className={`px-4 py-1.5 text-xs font-semibold disabled:opacity-40 disabled:cursor-not-allowed text-white rounded-lg transition-colors ${meta.submitCls}`}
            >
              Submit &amp; Resume
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
