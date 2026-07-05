import React, { useState, useEffect, useCallback } from 'react'
import { X, ChevronRight, ChevronLeft, Sparkles, Loader, Upload, Plus, Trash2, Check } from 'lucide-react'
import useStore from '../store/workflowStore'
import * as api from '../api/api'
import DataModelDesigner from './DataModelDesigner'

// ── Helpers ───────────────────────────────────────────────

function safeParseJSON(str) {
  try {
    return { value: JSON.parse(str), error: null }
  } catch (e) {
    return { value: null, error: e.message }
  }
}

function buildAssociationData({
  selectedModelId,
  project,
  environment,
  globalContextStr,
  inputMappings,
  defaultValueRows,
}) {
  const { value: globalContext } = safeParseJSON(globalContextStr || '{}')
  const defaultValues = {}
  defaultValueRows.forEach(({ key, value }) => {
    if (key.trim()) defaultValues[key.trim()] = value
  })

  const hasContent =
    selectedModelId ||
    project.trim() ||
    environment !== 'dev' ||
    (globalContext && Object.keys(globalContext).length > 0) ||
    inputMappings.some((m) => m.source.trim() || m.target.trim()) ||
    Object.keys(defaultValues).length > 0

  if (!hasContent) return null

  return {
    data_model_id: selectedModelId || null,
    project: project.trim(),
    environment,
    global_context: globalContext || {},
    input_mappings: inputMappings
      .filter((m) => m.source.trim() && m.target.trim())
      .map(({ source, target, description }) => ({ source, target, description })),
    default_values: defaultValues,
    validation_rules: [],
  }
}

// ── Step indicator ────────────────────────────────────────

function StepIndicator({ current, total }) {
  return (
    <div className="flex items-center gap-1">
      {Array.from({ length: total }, (_, i) => {
        const step = i + 1
        const active = step === current
        const done = step < current
        return (
          <React.Fragment key={step}>
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-colors ${
                done
                  ? 'bg-indigo-600 text-white'
                  : active
                  ? 'bg-indigo-500 text-white ring-2 ring-indigo-400/40'
                  : 'bg-slate-700 text-slate-400'
              }`}
            >
              {done ? <Check size={10} /> : step}
            </div>
            {step < total && (
              <div
                className={`h-px w-6 transition-colors ${done ? 'bg-indigo-600' : 'bg-slate-700'}`}
              />
            )}
          </React.Fragment>
        )
      })}
    </div>
  )
}

// ── Step 1 – Workflow Details ─────────────────────────────

function Step1({ name, setName, description, setDescription, project, setProject, environment, setEnvironment }) {
  return (
    <div className="space-y-4">
      <div>
        <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
          Workflow Name *
        </label>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="My Workflow"
          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
        />
      </div>
      <div>
        <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
          Description
        </label>
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="What does this workflow do?"
          rows={3}
          className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors resize-none"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
            Project
          </label>
          <input
            value={project}
            onChange={(e) => setProject(e.target.value)}
            placeholder="e.g. Finance Portal"
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
          />
        </div>
        <div>
          <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
            Environment
          </label>
          <select
            value={environment}
            onChange={(e) => setEnvironment(e.target.value)}
            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
          >
            <option value="dev">Dev</option>
            <option value="uat">UAT</option>
            <option value="prod">Prod</option>
          </select>
        </div>
      </div>
    </div>
  )
}

// ── Step 2 – Data Model Association ──────────────────────

function Step2({
  dataModels,
  selectedModelId, setSelectedModelId,
  newModel, setNewModel,
  workflowName, workflowDescription,
}) {
  const [tab, setTab] = useState(
    selectedModelId ? 'select' : 'create'
  )
  const [importText, setImportText] = useState('')
  const [importPreview, setImportPreview] = useState(null)
  const [importError, setImportError] = useState('')
  const [isImporting, setIsImporting] = useState(false)
  const [isSuggesting, setIsSuggesting] = useState(false)
  const [suggestError, setSuggestError] = useState('')

  const selectedModel = dataModels.find((m) => m.id === selectedModelId) || null

  const handleImportPreview = async () => {
    setImportError('')
    setImportPreview(null)
    const text = importText.trim()
    if (!text) { setImportError('Paste a JSON schema first.'); return }
    const { value: parsed, error } = safeParseJSON(text)
    if (error) { setImportError(`Invalid JSON: ${error}`); return }
    setIsImporting(true)
    try {
      const result = await api.importDataModel(parsed)
      setImportPreview(result)
    } catch (e) {
      setImportError('Failed to parse schema. Check the format.')
    } finally {
      setIsImporting(false)
    }
  }

  const handleUseImport = () => {
    if (!importPreview) return
    setSelectedModelId(importPreview.id)
    setTab('select')
  }

  const handleAISuggest = async () => {
    setSuggestError('')
    setIsSuggesting(true)
    try {
      const result = await api.suggestDataModel(workflowName, workflowDescription)
      setNewModel(result)
      setTab('create')
    } catch {
      setSuggestError('AI suggestion failed. Try again.')
    } finally {
      setIsSuggesting(false)
    }
  }

  const TABS = [
    { id: 'select', label: 'Select Existing' },
    { id: 'create', label: 'Create New' },
    { id: 'import', label: 'Import JSON' },
  ]

  return (
    <div className="space-y-4">
      {/* AI Suggest button */}
      <div className="flex items-center justify-between">
        <p className="text-xs text-slate-400">
          Associate a data model to give this workflow structured context.
        </p>
        <button
          type="button"
          onClick={handleAISuggest}
          disabled={isSuggesting}
          className="flex items-center gap-1.5 text-xs bg-indigo-900/40 hover:bg-indigo-800/50 text-indigo-300 border border-indigo-600/40 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50 whitespace-nowrap"
        >
          {isSuggesting ? <Loader size={12} className="animate-spin" /> : <Sparkles size={12} />}
          AI Suggest
        </button>
      </div>
      {suggestError && <p className="text-red-400 text-xs">{suggestError}</p>}

      {/* Tab bar */}
      <div className="flex gap-1 bg-slate-800/60 rounded-lg p-1">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setTab(t.id)}
            className={`flex-1 text-xs py-1.5 rounded-md transition-colors font-medium ${
              tab === t.id
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Select Existing */}
      {tab === 'select' && (
        <div className="space-y-3">
          {dataModels.length === 0 ? (
            <p className="text-xs text-slate-500 italic text-center py-4">
              No models available. Create one or use the AI Suggest feature.
            </p>
          ) : (
            <>
              <select
                value={selectedModelId || ''}
                onChange={(e) => setSelectedModelId(e.target.value || null)}
                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-indigo-500 transition-colors"
              >
                <option value="">-- Select a data model --</option>
                {dataModels.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.name}
                  </option>
                ))}
              </select>

              {selectedModel && (
                <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 space-y-2">
                  <p className="text-xs font-medium text-slate-200">{selectedModel.name}</p>
                  {selectedModel.description && (
                    <p className="text-xs text-slate-400">{selectedModel.description}</p>
                  )}
                  <div className="flex flex-wrap gap-1.5 mt-1">
                    {selectedModel.entities.map((e) => (
                      <span
                        key={e.id}
                        className="inline-flex items-center gap-1 bg-indigo-900/30 border border-indigo-700/40 text-indigo-300 text-[10px] px-2 py-0.5 rounded-full"
                      >
                        {e.name || 'Unnamed'}
                        <span className="text-indigo-400/60">{e.fields.length}f</span>
                      </span>
                    ))}
                    {selectedModel.entities.length === 0 && (
                      <span className="text-xs text-slate-500">No entities defined</span>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* Create New */}
      {tab === 'create' && (
        <div className="max-h-80 overflow-y-auto pr-1">
          <DataModelDesigner
            value={newModel}
            onChange={(updated) => setNewModel(updated)}
          />
        </div>
      )}

      {/* Import JSON */}
      {tab === 'import' && (
        <div className="space-y-3">
          <div>
            <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
              Paste JSON Schema
            </label>
            <textarea
              value={importText}
              onChange={(e) => { setImportText(e.target.value); setImportError(''); setImportPreview(null) }}
              placeholder={'{\n  "$schema": "http://json-schema.org/draft-07/schema",\n  "definitions": { ... }\n}'}
              rows={6}
              className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs text-slate-300 placeholder-slate-500 font-mono focus:outline-none focus:border-indigo-500 transition-colors resize-none"
            />
          </div>
          {importError && <p className="text-red-400 text-xs">{importError}</p>}
          <button
            type="button"
            onClick={handleImportPreview}
            disabled={isImporting}
            className="flex items-center gap-1.5 text-xs bg-slate-700 hover:bg-slate-600 text-slate-200 border border-slate-600 px-3 py-1.5 rounded-lg transition-colors disabled:opacity-50"
          >
            {isImporting ? <Loader size={12} className="animate-spin" /> : <Upload size={12} />}
            Preview
          </button>
          {importPreview && (
            <div className="bg-slate-800/60 border border-slate-700 rounded-lg p-3 space-y-2">
              <p className="text-xs font-medium text-slate-200">{importPreview.name}</p>
              <div className="flex flex-wrap gap-1.5">
                {importPreview.entities.map((e) => (
                  <span
                    key={e.id}
                    className="inline-flex items-center gap-1 bg-emerald-900/30 border border-emerald-700/40 text-emerald-300 text-[10px] px-2 py-0.5 rounded-full"
                  >
                    {e.name}
                    <span className="text-emerald-400/60">{e.fields.length}f</span>
                  </span>
                ))}
                {importPreview.entities.length === 0 && (
                  <span className="text-xs text-slate-400">No entities parsed</span>
                )}
              </div>
              <button
                type="button"
                onClick={handleUseImport}
                className="text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg transition-colors"
              >
                Use this model
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Step 3 – Context Config ───────────────────────────────

function Step3({
  globalContextStr, setGlobalContextStr,
  inputMappings, setInputMappings,
  defaultValueRows, setDefaultValueRows,
}) {
  const { error: gcError } = safeParseJSON(globalContextStr || '{}')

  const addMapping = () =>
    setInputMappings([...inputMappings, { source: '', target: '', description: '' }])

  const removeMapping = (i) =>
    setInputMappings(inputMappings.filter((_, idx) => idx !== i))

  const updateMapping = (i, patch) =>
    setInputMappings(inputMappings.map((m, idx) => (idx === i ? { ...m, ...patch } : m)))

  const addDefault = () => setDefaultValueRows([...defaultValueRows, { key: '', value: '' }])
  const removeDefault = (i) => setDefaultValueRows(defaultValueRows.filter((_, idx) => idx !== i))
  const updateDefault = (i, patch) =>
    setDefaultValueRows(defaultValueRows.map((r, idx) => (idx === i ? { ...r, ...patch } : r)))

  return (
    <div className="space-y-5">
      {/* Global Context */}
      <div>
        <label className="block text-[10px] font-medium text-slate-400 uppercase tracking-wide mb-1">
          Global Context
        </label>
        <p className="text-xs text-slate-500 mb-2">
          A JSON object available to all agents in this workflow run.
        </p>
        <textarea
          value={globalContextStr}
          onChange={(e) => setGlobalContextStr(e.target.value)}
          placeholder={'{\n  "customer": {},\n  "loan": {}\n}'}
          rows={4}
          className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-xs text-slate-300 placeholder-slate-500 font-mono focus:outline-none transition-colors resize-none ${
            gcError && globalContextStr ? 'border-red-500 focus:border-red-400' : 'border-slate-600 focus:border-indigo-500'
          }`}
        />
        {gcError && globalContextStr && (
          <p className="text-red-400 text-xs mt-1">Invalid JSON: {gcError}</p>
        )}
      </div>

      {/* Input Mappings */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">
            Input Mappings
          </label>
          <button
            type="button"
            onClick={addMapping}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <Plus size={11} /> Add
          </button>
        </div>
        <p className="text-xs text-slate-500 mb-2">
          Map data sources to workflow input targets (e.g. <code className="text-slate-400">request.body</code> → <code className="text-slate-400">customer.id</code>).
        </p>
        {inputMappings.length === 0 ? (
          <p className="text-xs text-slate-600 italic">No mappings defined.</p>
        ) : (
          <div className="space-y-2">
            {inputMappings.map((m, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <input
                  value={m.source}
                  onChange={(e) => updateMapping(i, { source: e.target.value })}
                  placeholder="source"
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <span className="text-slate-500 text-xs">→</span>
                <input
                  value={m.target}
                  onChange={(e) => updateMapping(i, { target: e.target.value })}
                  placeholder="target"
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <input
                  value={m.description}
                  onChange={(e) => updateMapping(i, { description: e.target.value })}
                  placeholder="desc"
                  className="w-24 bg-slate-800 border border-slate-600 rounded-lg px-2 py-1.5 text-xs text-slate-300 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => removeMapping(i)}
                  className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Default Values */}
      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">
            Default Values
          </label>
          <button
            type="button"
            onClick={addDefault}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <Plus size={11} /> Add
          </button>
        </div>
        <p className="text-xs text-slate-500 mb-2">
          Key=value pairs used as fallbacks when input data is missing.
        </p>
        {defaultValueRows.length === 0 ? (
          <p className="text-xs text-slate-600 italic">No defaults defined.</p>
        ) : (
          <div className="space-y-2">
            {defaultValueRows.map((r, i) => (
              <div key={i} className="flex items-center gap-2 group">
                <input
                  value={r.key}
                  onChange={(e) => updateDefault(i, { key: e.target.value })}
                  placeholder="key"
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <span className="text-slate-500 text-xs">=</span>
                <input
                  value={r.value}
                  onChange={(e) => updateDefault(i, { value: e.target.value })}
                  placeholder="value"
                  className="flex-1 bg-slate-800 border border-slate-600 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => removeDefault(i)}
                  className="p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 size={11} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// ── Main Modal ────────────────────────────────────────────

export default function SaveWorkflowModal() {
  const {
    isSaveModalOpen, closeSaveModal,
    workflowName: storeName,
    workflowDescription: storeDesc,
    currentAssociation,
    dataModels,
    loadDataModels,
    saveWithAssociation,
    isSaving,
  } = useStore()

  const [step, setStep] = useState(1)
  const TOTAL_STEPS = 3

  // Step 1 state
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [project, setProject] = useState('')
  const [environment, setEnvironment] = useState('dev')

  // Step 2 state
  const [selectedModelId, setSelectedModelId] = useState(null)
  const [newModel, setNewModel] = useState(null)

  // Step 3 state
  const [globalContextStr, setGlobalContextStr] = useState('{}')
  const [inputMappings, setInputMappings] = useState([])
  const [defaultValueRows, setDefaultValueRows] = useState([])

  // Pre-fill when modal opens
  useEffect(() => {
    if (!isSaveModalOpen) return

    setStep(1)
    setName(storeName || '')
    setDescription(storeDesc || '')
    setProject(currentAssociation?.project || '')
    setEnvironment(currentAssociation?.environment || 'dev')
    setSelectedModelId(currentAssociation?.data_model_id || null)
    setNewModel(null)

    // Pre-fill context
    const gc = currentAssociation?.global_context
    setGlobalContextStr(
      gc && Object.keys(gc).length > 0 ? JSON.stringify(gc, null, 2) : '{}'
    )
    setInputMappings(
      (currentAssociation?.input_mappings || []).map((m) => ({
        source: m.source,
        target: m.target,
        description: m.description || '',
      }))
    )
    const dv = currentAssociation?.default_values || {}
    setDefaultValueRows(Object.entries(dv).map(([key, value]) => ({ key, value: String(value) })))

    // Load fresh data models
    loadDataModels()
  }, [isSaveModalOpen])

  const handleCancel = useCallback(() => {
    closeSaveModal()
    setStep(1)
  }, [closeSaveModal])

  const handleSave = useCallback(async () => {
    if (!name.trim()) return

    // If the user created a new model in the designer, use that
    let finalModelId = selectedModelId
    if (!finalModelId && newModel?.name?.trim()) {
      try {
        const created = await api.createDataModel({
          name: newModel.name,
          description: newModel.description || '',
          entities: newModel.entities || [],
          relationships: newModel.relationships || [],
        })
        finalModelId = created.id
      } catch {
        // If creation fails, proceed without model
      }
    }

    const assocData = buildAssociationData({
      selectedModelId: finalModelId,
      project,
      environment,
      globalContextStr,
      inputMappings,
      defaultValueRows,
    })

    await saveWithAssociation(
      { name: name.trim(), description: description.trim() },
      assocData
    )
  }, [
    name, description, selectedModelId, newModel,
    project, environment, globalContextStr,
    inputMappings, defaultValueRows, saveWithAssociation,
  ])

  if (!isSaveModalOpen) return null

  const canGoBack = step > 1
  const canGoNext = step < TOTAL_STEPS
  const nameValid = name.trim().length > 0

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/60" onClick={handleCancel} />

      {/* Modal card */}
      <div className="relative bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 flex-shrink-0">
          <div className="flex items-center gap-4">
            <h2 className="text-sm font-semibold text-slate-100">Save Workflow</h2>
            <StepIndicator current={step} total={TOTAL_STEPS} />
          </div>
          <button
            type="button"
            onClick={handleCancel}
            className="p-1.5 text-slate-500 hover:text-slate-300 hover:bg-slate-800 rounded-lg transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Step label */}
        <div className="px-6 pt-4 pb-1 flex-shrink-0">
          <p className="text-[10px] font-medium text-slate-400 uppercase tracking-wide">
            {step === 1 && 'Step 1 — Workflow Details'}
            {step === 2 && 'Step 2 — Data Model (optional)'}
            {step === 3 && 'Step 3 — Context Config (optional)'}
          </p>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-4">
          {step === 1 && (
            <Step1
              name={name} setName={setName}
              description={description} setDescription={setDescription}
              project={project} setProject={setProject}
              environment={environment} setEnvironment={setEnvironment}
            />
          )}
          {step === 2 && (
            <Step2
              dataModels={dataModels}
              selectedModelId={selectedModelId}
              setSelectedModelId={setSelectedModelId}
              newModel={newModel}
              setNewModel={setNewModel}
              workflowName={name}
              workflowDescription={description}
            />
          )}
          {step === 3 && (
            <Step3
              globalContextStr={globalContextStr} setGlobalContextStr={setGlobalContextStr}
              inputMappings={inputMappings} setInputMappings={setInputMappings}
              defaultValueRows={defaultValueRows} setDefaultValueRows={setDefaultValueRows}
            />
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-slate-800 flex-shrink-0 gap-3">
          {/* Left: Cancel + Back */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleCancel}
              className="text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors"
            >
              Cancel
            </button>
            {canGoBack && (
              <button
                type="button"
                onClick={() => setStep((s) => s - 1)}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors"
              >
                <ChevronLeft size={13} />
                Back
              </button>
            )}
          </div>

          {/* Right: Skip / Next + Save */}
          <div className="flex items-center gap-2">
            {/* Skip (steps 2 and 3) */}
            {step > 1 && canGoNext && (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                className="text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors"
              >
                Skip
              </button>
            )}

            {/* Next */}
            {canGoNext && (
              <button
                type="button"
                onClick={() => setStep((s) => s + 1)}
                disabled={step === 1 && !nameValid}
                className="flex items-center gap-1 text-xs text-slate-300 hover:text-white hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-600 transition-colors disabled:opacity-40"
              >
                Next
                <ChevronRight size={13} />
              </button>
            )}

            {/* Save — always visible */}
            <button
              type="button"
              onClick={handleSave}
              disabled={isSaving || !nameValid}
              className="flex items-center gap-1.5 text-xs bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-1.5 rounded-lg transition-colors disabled:opacity-50 font-medium"
            >
              {isSaving ? <Loader size={12} className="animate-spin" /> : null}
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
