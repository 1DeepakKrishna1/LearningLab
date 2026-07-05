import React from 'react'
import { Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react'

const FIELD_TYPES = ['string', 'number', 'boolean', 'date', 'object', 'array']
const RELATION_TYPES = [
  { value: 'one_to_one', label: '1 : 1' },
  { value: 'one_to_many', label: '1 : N' },
  { value: 'many_to_many', label: 'N : N' },
]

function newField() {
  return { name: '', field_type: 'string', required: false, description: '' }
}

function newEntity() {
  return { id: crypto.randomUUID(), name: '', description: '', fields: [] }
}

function newRelationship(entities) {
  const fromId = entities[0]?.id || ''
  const toId = entities[1]?.id || entities[0]?.id || ''
  return {
    id: crypto.randomUUID(),
    from_entity: fromId,
    to_entity: toId,
    relation_type: 'one_to_many',
    label: '',
  }
}

// ── Sub-component: single entity editor ──────────────────

function EntityEditor({ entity, index, onChange, onRemove, isOnly }) {
  const [collapsed, setCollapsed] = React.useState(false)

  const updateField = (fi, patch) => {
    const updated = entity.fields.map((f, i) => (i === fi ? { ...f, ...patch } : f))
    onChange({ ...entity, fields: updated })
  }

  const addField = () => onChange({ ...entity, fields: [...entity.fields, newField()] })

  const removeField = (fi) =>
    onChange({ ...entity, fields: entity.fields.filter((_, i) => i !== fi) })

  return (
    <div className="border border-slate-700 rounded-xl bg-slate-800/60 overflow-hidden">
      {/* Entity header */}
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-800 border-b border-slate-700">
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="text-slate-400 hover:text-slate-200 transition-colors"
        >
          {collapsed ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
        </button>
        <input
          value={entity.name}
          onChange={(e) => onChange({ ...entity, name: e.target.value })}
          placeholder={`Entity ${index + 1} name`}
          className="flex-1 bg-transparent text-sm font-medium text-slate-100 placeholder-slate-500 focus:outline-none"
        />
        {!isOnly && (
          <button
            type="button"
            onClick={onRemove}
            className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors"
            title="Remove entity"
          >
            <Trash2 size={13} />
          </button>
        )}
      </div>

      {!collapsed && (
        <div className="p-3 space-y-3">
          {/* Entity description */}
          <input
            value={entity.description}
            onChange={(e) => onChange({ ...entity, description: e.target.value })}
            placeholder="Entity description (optional)"
            className="w-full bg-slate-700/50 border border-slate-600 rounded-lg px-3 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />

          {/* Fields */}
          <div className="space-y-2">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">Fields</p>
            {entity.fields.length === 0 && (
              <p className="text-xs text-slate-500 italic">No fields yet. Add one below.</p>
            )}
            {entity.fields.map((field, fi) => (
              <div key={fi} className="flex items-center gap-2 group">
                <input
                  value={field.name}
                  onChange={(e) => updateField(fi, { name: e.target.value })}
                  placeholder="field_name"
                  className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors min-w-0"
                />
                <select
                  value={field.field_type}
                  onChange={(e) => updateField(fi, { field_type: e.target.value })}
                  className="bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                >
                  {FIELD_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
                <label className="flex items-center gap-1 text-xs text-slate-400 cursor-pointer whitespace-nowrap">
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(e) => updateField(fi, { required: e.target.checked })}
                    className="accent-indigo-500"
                  />
                  req
                </label>
                <input
                  value={field.description}
                  onChange={(e) => updateField(fi, { description: e.target.value })}
                  placeholder="desc"
                  className="w-28 bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => removeField(fi)}
                  className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                  title="Remove field"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addField}
              className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors mt-1"
            >
              <Plus size={12} />
              Add Field
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Main component ────────────────────────────────────────

export default function DataModelDesigner({ value, onChange }) {
  const model = value || {
    id: crypto.randomUUID(),
    name: '',
    description: '',
    entities: [],
    relationships: [],
  }

  const update = (patch) => onChange({ ...model, ...patch })

  const addEntity = () => update({ entities: [...model.entities, newEntity()] })

  const removeEntity = (i) => {
    const removed = model.entities[i]
    const entities = model.entities.filter((_, idx) => idx !== i)
    // Remove relationships that reference removed entity
    const relationships = model.relationships.filter(
      (r) => r.from_entity !== removed.id && r.to_entity !== removed.id
    )
    update({ entities, relationships })
  }

  const updateEntity = (i, updated) => {
    update({ entities: model.entities.map((e, idx) => (idx === i ? updated : e)) })
  }

  const addRelationship = () => {
    if (model.entities.length < 2) return
    update({ relationships: [...model.relationships, newRelationship(model.entities)] })
  }

  const removeRelationship = (i) =>
    update({ relationships: model.relationships.filter((_, idx) => idx !== i) })

  const updateRelationship = (i, patch) =>
    update({
      relationships: model.relationships.map((r, idx) => (idx === i ? { ...r, ...patch } : r)),
    })

  return (
    <div className="space-y-4">
      {/* Model name & description */}
      <div className="space-y-2">
        <div>
          <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
            Model Name *
          </label>
          <input
            value={model.name}
            onChange={(e) => update({ name: e.target.value })}
            placeholder="e.g. Customer Data Model"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
            Description
          </label>
          <input
            value={model.description}
            onChange={(e) => update({ description: e.target.value })}
            placeholder="Optional description"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
      </div>

      {/* Entities */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">Entities</p>
          <button
            type="button"
            onClick={addEntity}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 border border-indigo-500/40 hover:border-indigo-400 rounded-lg px-2 py-1 transition-colors"
          >
            <Plus size={12} />
            Add Entity
          </button>
        </div>
        {model.entities.length === 0 ? (
          <p className="text-xs text-slate-500 italic text-center py-3">
            No entities yet. Click "Add Entity" to start.
          </p>
        ) : (
          <div className="space-y-2">
            {model.entities.map((entity, i) => (
              <EntityEditor
                key={entity.id}
                entity={entity}
                index={i}
                onChange={(updated) => updateEntity(i, updated)}
                onRemove={() => removeEntity(i)}
                isOnly={model.entities.length === 1}
              />
            ))}
          </div>
        )}
      </div>

      {/* Relationships */}
      {model.entities.length >= 2 && (
        <div>
          <div className="flex items-center justify-between mb-2">
            <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">
              Relationships
            </p>
            <button
              type="button"
              onClick={addRelationship}
              className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 border border-indigo-500/40 hover:border-indigo-400 rounded-lg px-2 py-1 transition-colors"
            >
              <Plus size={12} />
              Add Relationship
            </button>
          </div>
          {model.relationships.length === 0 ? (
            <p className="text-xs text-slate-500 italic text-center py-2">
              No relationships defined.
            </p>
          ) : (
            <div className="space-y-2">
              {model.relationships.map((rel, i) => (
                <div
                  key={rel.id}
                  className="flex items-center gap-2 bg-slate-800/60 border border-slate-700 rounded-lg px-3 py-2 group"
                >
                  <select
                    value={rel.from_entity}
                    onChange={(e) => updateRelationship(i, { from_entity: e.target.value })}
                    className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {model.entities.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.name || `Entity ${model.entities.indexOf(e) + 1}`}
                      </option>
                    ))}
                  </select>
                  <select
                    value={rel.relation_type}
                    onChange={(e) => updateRelationship(i, { relation_type: e.target.value })}
                    className="bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {RELATION_TYPES.map((rt) => (
                      <option key={rt.value} value={rt.value}>
                        {rt.label}
                      </option>
                    ))}
                  </select>
                  <select
                    value={rel.to_entity}
                    onChange={(e) => updateRelationship(i, { to_entity: e.target.value })}
                    className="flex-1 bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors"
                  >
                    {model.entities.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.name || `Entity ${model.entities.indexOf(e) + 1}`}
                      </option>
                    ))}
                  </select>
                  <input
                    value={rel.label}
                    onChange={(e) => updateRelationship(i, { label: e.target.value })}
                    placeholder="label"
                    className="w-20 bg-slate-700/50 border border-slate-600 rounded-lg px-2 py-1 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                  />
                  <button
                    type="button"
                    onClick={() => removeRelationship(i)}
                    className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={11} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
