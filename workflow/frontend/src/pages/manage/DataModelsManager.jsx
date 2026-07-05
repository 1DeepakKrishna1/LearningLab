import { useState, useEffect } from 'react'
import { getDataModels, createDataModel, updateDataModel, deleteDataModel } from '../../api/api'
import {
  Database, Plus, Pencil, Trash2, X, Loader2, AlertCircle, Calendar, Tag,
  ChevronDown, ChevronRight
} from 'lucide-react'

const FIELD_TYPES = ['string', 'number', 'boolean', 'date', 'object', 'array']

function uid() {
  return typeof crypto !== 'undefined' && crypto.randomUUID
    ? crypto.randomUUID()
    : Math.random().toString(36).slice(2) + Date.now().toString(36)
}

function parseDefault(raw) {
  if (!raw || raw.trim() === '' || raw.trim() === 'null') return null
  try { return JSON.parse(raw.trim()) } catch { return raw }
}

function showDefault(v) {
  if (v === null || v === undefined) return ''
  return typeof v === 'string' ? v : JSON.stringify(v)
}

function emptyField() {
  return { name: '', field_type: 'string', required: false, description: '', validation: null, default_value: null }
}

function emptyEntity() {
  return { id: uid(), name: '', description: '', fields: [] }
}

function cloneEntities(entities) {
  return (entities || []).map(e => ({ ...e, fields: (e.fields || []).map(f => ({ ...f })) }))
}

// ── Wide modal (for add/edit) ───────────────────────────────

function WideModal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-4xl shadow-2xl flex flex-col max-h-[90vh]">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700 shrink-0">
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

function SmallModal({ title, onClose, children }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl">
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
          <h2 className="text-white font-semibold">{title}</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={18} />
          </button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  )
}

// ── Field row ───────────────────────────────────────────────

function FieldRow({ field, onChange, onDelete }) {
  return (
    <div className="grid grid-cols-[1fr_88px_28px_1.5fr_80px_20px] gap-1.5 items-center">
      <input
        value={field.name}
        onChange={e => onChange({ ...field, name: e.target.value })}
        placeholder="field_name"
        className="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] text-indigo-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono min-w-0"
      />
      <select
        value={field.field_type}
        onChange={e => onChange({ ...field, field_type: e.target.value })}
        className="bg-slate-950 border border-slate-700 rounded px-1.5 py-1.5 text-[11px] text-slate-200 focus:outline-none focus:border-indigo-500"
      >
        {FIELD_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
      </select>
      <label className="flex items-center justify-center cursor-pointer" title="Required">
        <input
          type="checkbox"
          checked={!!field.required}
          onChange={e => onChange({ ...field, required: e.target.checked })}
          className="accent-indigo-500 w-3.5 h-3.5"
        />
      </label>
      <input
        value={field.description}
        onChange={e => onChange({ ...field, description: e.target.value })}
        placeholder="description"
        className="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500 min-w-0"
      />
      <input
        value={showDefault(field.default_value)}
        onChange={e => onChange({ ...field, default_value: parseDefault(e.target.value) })}
        placeholder="default"
        className="bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-[11px] text-slate-400 placeholder-slate-600 focus:outline-none focus:border-indigo-500 font-mono min-w-0"
      />
      <button
        type="button"
        onClick={onDelete}
        className="flex justify-center p-1 text-slate-600 hover:text-red-400 transition-colors"
      >
        <X size={12} />
      </button>
    </div>
  )
}

// ── Entity card (collapsible) ───────────────────────────────

function EntityCard({ entity, onChange, onDelete }) {
  const [open, setOpen] = useState(!entity.name)

  function updateField(i, f) {
    onChange({ ...entity, fields: entity.fields.map((ff, idx) => idx === i ? f : ff) })
  }

  function addField() {
    onChange({ ...entity, fields: [...entity.fields, emptyField()] })
    setOpen(true)
  }

  function removeField(i) {
    onChange({ ...entity, fields: entity.fields.filter((_, idx) => idx !== i) })
  }

  return (
    <div className="border border-slate-700 rounded-lg overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2.5 bg-slate-800/80">
        <button
          type="button"
          onClick={() => setOpen(v => !v)}
          className="text-slate-400 hover:text-white transition-colors shrink-0"
        >
          {open ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
        </button>
        <input
          value={entity.name}
          onChange={e => onChange({ ...entity, name: e.target.value })}
          placeholder="EntityName"
          className="flex-1 bg-transparent text-sm text-white placeholder-slate-500 focus:outline-none font-medium min-w-0"
        />
        <span className="text-[10px] text-slate-500 shrink-0">{entity.fields.length} fields</span>
        <button
          type="button"
          onClick={onDelete}
          className="p-1 text-slate-600 hover:text-red-400 transition-colors shrink-0"
          title="Remove entity"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {open && (
        <div className="px-3 py-3 bg-slate-900/40 space-y-3">
          <input
            value={entity.description}
            onChange={e => onChange({ ...entity, description: e.target.value })}
            placeholder="Entity description (optional)"
            className="w-full bg-slate-950 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500"
          />

          {entity.fields.length > 0 && (
            <>
              <div className="grid grid-cols-[1fr_88px_28px_1.5fr_80px_20px] gap-1.5">
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Name</span>
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Type</span>
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide text-center">Req</span>
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Description</span>
                <span className="text-[10px] font-medium text-slate-500 uppercase tracking-wide">Default</span>
                <span />
              </div>
              <div className="space-y-1.5">
                {entity.fields.map((f, i) => (
                  <FieldRow
                    key={i}
                    field={f}
                    onChange={ff => updateField(i, ff)}
                    onDelete={() => removeField(i)}
                  />
                ))}
              </div>
            </>
          )}

          <button
            type="button"
            onClick={addField}
            className="flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <Plus size={12} /> Add Field
          </button>
        </div>
      )}
    </div>
  )
}

// ── Data model form ─────────────────────────────────────────

function DataModelForm({ initial, onSave, onClose, saving }) {
  const [name, setName] = useState(initial?.name || '')
  const [description, setDescription] = useState(initial?.description || '')
  const [entities, setEntities] = useState(() => cloneEntities(initial?.entities))

  function updateEntity(i, e) {
    setEntities(prev => prev.map((ee, idx) => idx === i ? e : ee))
  }

  function addEntity() {
    setEntities(prev => [...prev, emptyEntity()])
  }

  function removeEntity(i) {
    setEntities(prev => prev.filter((_, idx) => idx !== i))
  }

  function handleSubmit(e) {
    e.preventDefault()
    onSave({ name, description, entities, relationships: initial?.relationships || [] })
  }

  return (
    <form onSubmit={handleSubmit}>
      <div className="space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Name <span className="text-red-400">*</span></label>
          <input
            required
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            placeholder="Data model name"
          />
        </div>

        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            rows={2}
            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            placeholder="Describe this data model…"
          />
        </div>

        <div>
          <div className="flex items-center justify-between mb-2">
            <label className="text-xs font-medium text-slate-400">
              Entities <span className="text-slate-600 font-normal ml-1">({entities.length})</span>
            </label>
          </div>
          <div className="space-y-2">
            {entities.length === 0 && (
              <p className="text-[11px] text-slate-500 italic py-1">No entities defined.</p>
            )}
            {entities.map((e, i) => (
              <EntityCard
                key={e.id || i}
                entity={e}
                onChange={ee => updateEntity(i, ee)}
                onDelete={() => removeEntity(i)}
              />
            ))}
          </div>
          <button
            type="button"
            onClick={addEntity}
            className="mt-2.5 flex items-center gap-1.5 text-[11px] text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <Plus size={12} /> Add Entity
          </button>
        </div>
      </div>

      <div className="flex gap-3 justify-end mt-6 pt-4 border-t border-slate-700 shrink-0">
        <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="px-4 py-2 text-sm text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {saving && <Loader2 size={14} className="animate-spin" />}
          {initial ? 'Save Changes' : 'Create Model'}
        </button>
      </div>
    </form>
  )
}

// ── Confirm delete ──────────────────────────────────────────

function ConfirmDelete({ model, onConfirm, onClose, loading }) {
  return (
    <SmallModal title="Delete Data Model" onClose={onClose}>
      <p className="text-slate-300 text-sm mb-4">
        Are you sure you want to delete <span className="text-white font-medium">"{model.name}"</span>? All entities and relationships will be permanently removed.
      </p>
      <div className="flex gap-3 justify-end">
        <button onClick={onClose} className="px-4 py-2 text-sm text-slate-300 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors">
          Cancel
        </button>
        <button
          onClick={onConfirm}
          disabled={loading}
          className="px-4 py-2 text-sm text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors disabled:opacity-50 flex items-center gap-2"
        >
          {loading && <Loader2 size={14} className="animate-spin" />}
          Delete
        </button>
      </div>
    </SmallModal>
  )
}

// ── Main page ───────────────────────────────────────────────

export default function DataModelsManager() {
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [modalState, setModalState] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => { loadModels() }, [])

  async function loadModels() {
    try {
      setLoading(true)
      const data = await getDataModels()
      setModels(data)
    } catch {
      setError('Failed to load data models.')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave(form) {
    try {
      setSaving(true)
      if (modalState.type === 'add') {
        await createDataModel(form)
      } else {
        await updateDataModel(modalState.model.id, form)
      }
      setModalState(null)
      loadModels()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    try {
      setSaving(true)
      await deleteDataModel(modalState.model.id)
      setModalState(null)
      loadModels()
    } catch {
      /* silently ignore */
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-white">Data Models</h1>
          <p className="text-slate-400 text-sm mt-1">Define schemas for your workflow data structures.</p>
        </div>
        <button
          onClick={() => setModalState({ type: 'add' })}
          className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
        >
          <Plus size={16} /> New Data Model
        </button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20 text-slate-400">
          <Loader2 size={24} className="animate-spin mr-2" /> Loading data models…
        </div>
      ) : error ? (
        <div className="flex items-center gap-2 text-red-400 py-10"><AlertCircle size={18} /> {error}</div>
      ) : (
        <div className="bg-slate-800 rounded-xl border border-slate-700 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-900">
              <tr>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Name</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Entities</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden xl:table-cell">Entity Names</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3">Relationships</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden md:table-cell">Description</th>
                <th className="text-left text-xs font-medium text-slate-400 px-4 py-3 hidden lg:table-cell">Created</th>
                <th className="text-right text-xs font-medium text-slate-400 px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700">
              {models.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center text-slate-500 py-10">
                    <Database size={32} className="mx-auto mb-2 opacity-30" />
                    No data models yet. Create one to get started.
                  </td>
                </tr>
              ) : (
                models.map(m => (
                  <tr key={m.id} className="hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3">
                      <p className="font-medium text-white">{m.name}</p>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full text-xs font-medium">
                        {(m.entities || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3 hidden xl:table-cell">
                      <div className="flex flex-wrap gap-1">
                        {(m.entities || []).slice(0, 4).map((e, i) => (
                          <span key={i} className="inline-flex items-center gap-1 bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded text-xs">
                            <Tag size={9} />{typeof e === 'string' ? e : (e.name || 'Entity')}
                          </span>
                        ))}
                        {(m.entities || []).length > 4 && (
                          <span className="text-slate-500 text-xs self-center">+{m.entities.length - 4}</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center bg-slate-700 text-slate-300 px-2 py-0.5 rounded-full text-xs font-medium">
                        {(m.relationships || []).length}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-slate-400 max-w-xs truncate hidden md:table-cell">{m.description || '—'}</td>
                    <td className="px-4 py-3 text-slate-400 text-xs hidden lg:table-cell">
                      <span className="flex items-center gap-1">
                        <Calendar size={12} />
                        {m.created_at ? new Date(m.created_at).toLocaleDateString() : '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setModalState({ type: 'edit', model: m })}
                          className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition-colors"
                          title="Edit"
                        >
                          <Pencil size={14} />
                        </button>
                        <button
                          onClick={() => setModalState({ type: 'delete', model: m })}
                          className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors"
                          title="Delete"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      {modalState?.type === 'add' && (
        <WideModal title="New Data Model" onClose={() => setModalState(null)}>
          <DataModelForm onSave={handleSave} onClose={() => setModalState(null)} saving={saving} />
        </WideModal>
      )}
      {modalState?.type === 'edit' && (
        <WideModal title="Edit Data Model" onClose={() => setModalState(null)}>
          <DataModelForm
            initial={modalState.model}
            onSave={handleSave}
            onClose={() => setModalState(null)}
            saving={saving}
          />
        </WideModal>
      )}
      {modalState?.type === 'delete' && (
        <ConfirmDelete
          model={modalState.model}
          onConfirm={handleDelete}
          onClose={() => setModalState(null)}
          loading={saving}
        />
      )}
    </div>
  )
}
