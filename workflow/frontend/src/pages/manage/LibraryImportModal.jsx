import { useState, useRef } from 'react'
import {
  Upload, Loader2, AlertCircle, CheckCircle2, X,
  BookOpen, Bot, Wrench,
} from 'lucide-react'

const ACTION_LABELS = { add: 'Add', update: 'Update', skip: 'Skip' }
const ALLOWED_ACTIONS = { new: ['add', 'skip'], exists: ['update', 'skip'] }

const GROUP_META = {
  workflows: { title: 'Templates', icon: BookOpen, color: 'text-indigo-400' },
  agents:    { title: 'Agents',    icon: Bot,      color: 'text-purple-400' },
  tools:     { title: 'Tools',     icon: Wrench,   color: 'text-emerald-400' },
}

// Sections each import kind shows in the decisions step (in render order).
const KIND_SECTIONS = {
  tool:     ['tools'],
  agent:    ['agents', 'tools'],
  template: ['workflows', 'agents', 'tools'],
}

const KIND_LABELS = {
  tool:     { title: 'Import Tools',     verb: 'tool export' },
  agent:    { title: 'Import Agents',    verb: 'agent export' },
  template: { title: 'Import Templates', verb: 'template export' },
}

function ActionSelector({ value, onChange, status }) {
  const options = ALLOWED_ACTIONS[status] || ['add', 'update', 'skip']
  return (
    <div className="flex gap-1">
      {options.map(opt => (
        <button
          key={opt}
          onClick={() => onChange(opt)}
          className={`px-2 py-0.5 rounded text-xs font-medium transition-colors ${
            value === opt
              ? opt === 'skip'
                ? 'bg-slate-600 text-slate-200'
                : opt === 'update'
                  ? 'bg-amber-600 text-white'
                  : 'bg-emerald-600 text-white'
              : 'bg-slate-700 text-slate-400 hover:text-white'
          }`}
        >
          {ACTION_LABELS[opt]}
        </button>
      ))}
    </div>
  )
}

function StatusBadge({ status }) {
  return status === 'exists'
    ? <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30">Exists</span>
    : <span className="inline-flex px-1.5 py-0.5 rounded text-xs font-medium bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">New</span>
}

function EntityGroup({ groupKey, entities, decisions, onActionChange, onBulkAction }) {
  if (!entities || entities.length === 0) return null
  const meta = GROUP_META[groupKey] || { title: groupKey, icon: BookOpen, color: 'text-slate-400' }
  const Icon = meta.icon

  function handleBulk(action) {
    const map = Object.fromEntries(entities.map(e => {
      if (action === 'skip') return [e.id, 'skip']
      if (action === 'add' && e._status === 'new') return [e.id, 'add']
      if (action === 'update' && e._status === 'exists') return [e.id, 'update']
      return [e.id, decisions[e.id]]
    }))
    onBulkAction(map)
  }

  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Icon size={14} className={meta.color} />
          <span className="text-sm font-medium text-white">{meta.title} ({entities.length})</span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-xs text-slate-500 mr-1">All:</span>
          {['add', 'update', 'skip'].map(opt => (
            <button
              key={opt}
              onClick={() => handleBulk(opt)}
              className="px-2 py-0.5 rounded text-xs text-slate-400 hover:text-white bg-slate-700 hover:bg-slate-600 transition-colors"
            >
              {ACTION_LABELS[opt]}
            </button>
          ))}
        </div>
      </div>
      <div className="space-y-1">
        {entities.map(entity => (
          <div key={entity.id} className="flex items-center justify-between bg-slate-900 rounded-lg px-3 py-2">
            <div className="flex items-center gap-2 min-w-0">
              <StatusBadge status={entity._status} />
              <span className="text-sm text-slate-200 truncate">{entity.name}</span>
            </div>
            <ActionSelector
              value={decisions[entity.id] || 'skip'}
              onChange={v => onActionChange(entity.id, v)}
              status={entity._status}
            />
          </div>
        ))}
      </div>
    </div>
  )
}

function initDecisions(preview, sections) {
  const decide = s => s === 'exists' ? 'update' : 'add'
  const out = {}
  for (const key of sections) {
    out[key] = Object.fromEntries((preview[key] || []).map(e => [e.id, decide(e._status)]))
  }
  return out
}

function Modal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl max-h-[90vh] flex flex-col">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 flex-shrink-0">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
      </div>
    </div>
  )
}

/**
 * Reusable import dialog for library entities (tool/agent/template).
 *
 * Props:
 *  - kind: 'tool' | 'agent' | 'template'
 *  - previewFn(exportData): Promise<preview>
 *  - applyFn(exportData, decisions): Promise<result>
 *  - onClose(): void
 *  - onImported(): void   // called once after a successful apply
 */
export default function LibraryImportModal({ kind, previewFn, applyFn, onClose, onImported }) {
  const sections = KIND_SECTIONS[kind] || []
  const labels = KIND_LABELS[kind] || { title: 'Import', verb: 'export' }

  const fileRef = useRef(null)
  const [step, setStep] = useState('upload')   // upload | decisions | applying | done
  const [exportData, setExportData] = useState(null)
  const [preview, setPreview] = useState(null)
  const [decisions, setDecisions] = useState({})
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [dragOver, setDragOver] = useState(false)

  async function handleFile(file) {
    if (!file) return
    setError(null)
    try {
      const text = await file.text()
      const parsed = JSON.parse(text)
      // Basic shape check — at least the primary section must exist.
      const primary = sections[0]
      if (!Array.isArray(parsed[primary])) {
        throw new Error(`Missing "${primary}" — not a valid ${labels.verb} file.`)
      }
      setLoading(true)
      const prev = await previewFn(parsed)
      setExportData(parsed)
      setPreview(prev)
      setDecisions(initDecisions(prev, sections))
      setStep('decisions')
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to parse file.')
    } finally {
      setLoading(false)
    }
  }

  function onFilePick(e) { handleFile(e.target.files?.[0]) }
  function onDrop(e) {
    e.preventDefault(); setDragOver(false)
    handleFile(e.dataTransfer.files?.[0])
  }

  function setEntityAction(group, id, action) {
    setDecisions(d => ({ ...d, [group]: { ...d[group], [id]: action } }))
  }

  function setBulkAction(group, newMap) {
    setDecisions(d => ({ ...d, [group]: newMap }))
  }

  async function handleApply() {
    setStep('applying')
    setError(null)
    try {
      const res = await applyFn(exportData, decisions)
      setResult(res)
      setStep('done')
      onImported?.()
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Import failed.')
      setStep('decisions')
    }
  }

  const totalEntities = preview
    ? sections.reduce((sum, key) => sum + (preview[key]?.length || 0), 0)
    : 0

  return (
    <Modal title={labels.title} onClose={onClose}>
      {/* ── Step: Upload ── */}
      {step === 'upload' && (
        <div>
          <p className="text-sm text-slate-400 mb-4">
            Select a {labels.verb} JSON file to import. The system will show you what will be added or updated before applying changes.
          </p>
          <div
            onDragOver={e => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={onDrop}
            onClick={() => fileRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center cursor-pointer transition-colors ${
              dragOver ? 'border-indigo-400 bg-indigo-500/10' : 'border-slate-600 hover:border-slate-500 hover:bg-slate-700/30'
            }`}
          >
            <Upload size={32} className="text-slate-400 mb-3" />
            <p className="text-sm text-slate-300 font-medium">Drop your export file here</p>
            <p className="text-xs text-slate-500 mt-1">or click to browse</p>
            <p className="text-xs text-slate-600 mt-2">Accepts .json export files only</p>
          </div>
          <input ref={fileRef} type="file" accept=".json,application/json" className="hidden" onChange={onFilePick} />
          {loading && (
            <div className="flex items-center gap-2 justify-center mt-4 text-slate-400 text-sm">
              <Loader2 size={16} className="animate-spin" /> Validating file…
            </div>
          )}
          {error && (
            <div className="flex items-start gap-2 mt-4 text-red-400 text-sm bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
              <AlertCircle size={15} className="mt-0.5 flex-shrink-0" /> {error}
            </div>
          )}
          <div className="flex justify-end mt-5">
            <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── Step: Decisions ── */}
      {step === 'decisions' && preview && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <div>
              <p className="text-sm text-slate-300">
                <span className="text-white font-medium">{labels.title}</span>
                <span className="text-slate-500 ml-2 text-xs">Export ID: {preview.exportId}</span>
              </p>
              <p className="text-xs text-slate-500 mt-0.5">{totalEntities} entities found — choose an action for each.</p>
            </div>
          </div>

          {sections.map(key => (
            <EntityGroup
              key={key}
              groupKey={key}
              entities={preview[key] || []}
              decisions={decisions[key] || {}}
              onActionChange={(id, v) => setEntityAction(key, id, v)}
              onBulkAction={v => setBulkAction(key, v)}
            />
          ))}

          {error && (
            <div className="flex items-start gap-2 mb-3 text-red-400 text-sm bg-red-500/10 rounded-lg px-3 py-2 border border-red-500/20">
              <AlertCircle size={15} className="mt-0.5 flex-shrink-0" /> {error}
            </div>
          )}

          <div className="flex gap-3 justify-end pt-3 border-t border-slate-700">
            <button
              onClick={() => { setStep('upload'); setPreview(null); setExportData(null) }}
              className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
            >
              Back
            </button>
            <button
              onClick={handleApply}
              className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors flex items-center gap-2"
            >
              <CheckCircle2 size={14} /> Apply Import
            </button>
          </div>
        </div>
      )}

      {/* ── Step: Applying ── */}
      {step === 'applying' && (
        <div className="flex flex-col items-center justify-center py-12">
          <Loader2 size={32} className="animate-spin text-indigo-400 mb-3" />
          <p className="text-slate-300 text-sm">Applying import…</p>
        </div>
      )}

      {/* ── Step: Done ── */}
      {step === 'done' && result && (
        <div>
          <div className="flex items-center gap-2 mb-5">
            <CheckCircle2 size={20} className="text-emerald-400" />
            <span className="text-white font-medium">Import Complete</span>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-5 sm:grid-cols-4">
            {[
              { label: 'Added', count: result.added.length, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
              { label: 'Updated', count: result.updated.length, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
              { label: 'Skipped', count: result.skipped.length, color: 'text-slate-400', bg: 'bg-slate-700/50 border-slate-600' },
              { label: 'Errors', count: result.errors.length, color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/20' },
            ].map(s => (
              <div key={s.label} className={`rounded-lg border px-3 py-2.5 text-center ${s.bg}`}>
                <div className={`text-xl font-bold ${s.color}`}>{s.count}</div>
                <div className="text-xs text-slate-400 mt-0.5">{s.label}</div>
              </div>
            ))}
          </div>

          {result.errors.length > 0 && (
            <div className="mb-4 bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2">
              <p className="text-xs font-medium text-red-400 mb-1">Errors</p>
              {result.errors.map((e, i) => (
                <p key={i} className="text-xs text-red-300">{e.type}: {e.name} — {e.error}</p>
              ))}
            </div>
          )}

          <div className="flex justify-end">
            <button onClick={onClose} className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors">
              Done
            </button>
          </div>
        </div>
      )}
    </Modal>
  )
}
