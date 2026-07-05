import React, { useState, useRef } from 'react'
import {
  Play, Square, Save, BookmarkPlus, Plus, ChevronDown,
  Loader, CheckCircle, XCircle, Zap, Trash2, ArrowLeft,
  Clock, FileSpreadsheet, Mail, Hand,
} from 'lucide-react'
import useStore from '../store/workflowStore'
import usePortalStore from '../store/portalStore'
import ThemeSwitcher from './ThemeSwitcher'
import SaveWorkflowModal from './SaveWorkflowModal'

const TRIGGER_RUN_ICONS = {
  manual:       Hand,
  webhook:      Zap,
  cron:         Clock,
  google_sheet: FileSpreadsheet,
  email:        Mail,
}

const TRIGGER_RUN_LABELS = {
  manual:       'Manual run',
  webhook:      'HTTP Webhook',
  cron:         'Cron Schedule',
  google_sheet: 'Google Sheet Row',
  email:        'Email (Power Automate)',
}

const TRIGGER_DEFAULT_PAYLOADS = {
  webhook:      { source: 'studio_simulation', sample: true },
  cron:         { scheduled_for: new Date().toISOString() },
  google_sheet: { sheet_id: 'simulated', row: 1, values: { name: 'Sample', email: 'sample@example.com' } },
  email:        { from: 'sender@example.com', subject: 'Simulated email', body: 'This is a simulated email body.', received_at: new Date().toISOString() },
  manual:       {},
}

export default function Toolbar() {
  const {
    workflowName, setWorkflowName,
    workflowId,
    userWorkflows,
    nodes,
    isExecuting, executionStatus,
    isSaving,
    runExecution, stopExecution,
    saveWorkflow, saveWorkflowAs, newWorkflow,
    openSaveModal,
    loadWorkflow, deleteWorkflow,
    notification,
  } = useStore()
  const { returnToPortal, org } = usePortalStore()

  const [deleteTarget, setDeleteTarget] = useState(null) // { id, name }

  const [showWorkflows, setShowWorkflows] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [saveAsMode, setSaveAsMode] = useState(false)
  const [saveAsName, setSaveAsName] = useState('')
  const saveAsInputRef = useRef(null)
  const [showRunMenu, setShowRunMenu] = useState(false)

  // Pull triggers off the canvas Start node so the dropdown can list saved triggers.
  const startNode = nodes.find((n) => n.data?.type === 'start')
  const configuredTriggers = startNode?.data?.properties?.triggers || []

  const runWith = (opts) => {
    setShowRunMenu(false)
    runExecution(opts)
  }

  const enterSaveAs = () => {
    setSaveAsName(`${workflowName} (Copy)`)
    setSaveAsMode(true)
    setTimeout(() => saveAsInputRef.current?.select(), 0)
  }

  const commitSaveAs = () => {
    const name = saveAsName.trim()
    setSaveAsMode(false)
    if (name) saveWorkflowAs(name)
  }

  const statusIcon = () => {
    if (isExecuting) return <Loader size={14} className="animate-spin text-blue-400" />
    if (executionStatus === 'completed') return <CheckCircle size={14} className="text-green-400" />
    if (executionStatus === 'failed') return <XCircle size={14} className="text-red-400" />
    return null
  }

  return (
    <header className="h-14 flex items-center px-4 gap-3 bg-slate-900 border-b border-slate-800 flex-shrink-0 z-10">
      {/* Back to Portal */}
      <button
        onClick={returnToPortal}
        className="flex items-center gap-1 px-2 py-1 rounded text-xs text-slate-400 hover:text-slate-100 hover:bg-slate-700 transition-colors"
        title="Back to Portal"
      >
        <ArrowLeft size={13} />
        <span className="hidden sm:block">Portal</span>
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2 mr-2">
        {org.hasLogo && org.logoUrl && (
          <img src={org.logoUrl} alt={org.name} className="h-7 w-auto object-contain" onError={(e) => { e.target.style.display='none' }} />
        )}
        <span className="text-sm font-bold text-slate-100 hidden sm:block">Studio</span>
      </div>

      {/* Workflow name / selector */}
      <div className="relative">
        <div className="flex items-center gap-1">
          {editingName ? (
            <input
              autoFocus
              value={workflowName}
              onChange={(e) => setWorkflowName(e.target.value)}
              onBlur={() => setEditingName(false)}
              onKeyDown={(e) => e.key === 'Enter' && setEditingName(false)}
              className="bg-slate-800 border border-indigo-500 rounded px-2 py-1 text-sm text-slate-100 w-48 focus:outline-none"
            />
          ) : (
            <button
              onClick={() => setEditingName(true)}
              className="text-sm font-medium text-slate-200 hover:text-white px-2 py-1 rounded hover:bg-slate-700/50 transition-colors max-w-[180px] truncate"
              title="Click to rename"
            >
              {workflowName}
            </button>
          )}
          <button
            onClick={() => setShowWorkflows((v) => !v)}
            className="p-1 text-slate-500 hover:text-slate-300 hover:bg-slate-700/50 rounded transition-colors"
            title="Switch workflow"
          >
            <ChevronDown size={14} />
          </button>
        </div>

        {/* Workflow dropdown */}
        {showWorkflows && (
          <div className="absolute top-full left-0 mt-1 w-64 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden">
            <div className="px-3 py-2 border-b border-slate-700">
              <p className="text-[11px] text-slate-400 uppercase tracking-wide">My Workflows</p>
            </div>
            <div className="max-h-56 overflow-y-auto">
              {userWorkflows.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-4">No saved workflows</p>
              ) : (
                userWorkflows.map((wf) => (
                  <div
                    key={wf.id}
                    className={`group flex items-center px-3 py-2.5 hover:bg-slate-700 transition-colors ${
                      wf.id === workflowId ? 'bg-indigo-900/20' : ''
                    }`}
                  >
                    <button
                      onClick={() => { loadWorkflow(wf.id); setShowWorkflows(false) }}
                      className={`flex-1 text-left text-xs truncate ${
                        wf.id === workflowId ? 'text-indigo-300' : 'text-slate-200'
                      }`}
                    >
                      {wf.name}
                      {wf.id === workflowId && <span className="text-[9px] text-indigo-400 ml-2">current</span>}
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); setDeleteTarget({ id: wf.id, name: wf.name }); setShowWorkflows(false) }}
                      className="ml-2 flex-shrink-0 p-1 text-slate-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                      title="Delete workflow"
                    >
                      <Trash2 size={11} />
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      {/* Execution status */}
      {statusIcon() && (
        <div className="flex items-center gap-1 text-xs text-slate-400">
          {statusIcon()}
          <span className="hidden sm:block">
            {isExecuting ? 'Running…' : executionStatus === 'completed' ? 'Completed' : 'Failed'}
          </span>
        </div>
      )}

      {/* Spacer */}
      <div className="flex-1" />

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <ThemeSwitcher />

        <button
          onClick={newWorkflow}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors"
        >
          <Plus size={13} />
          <span className="hidden sm:block">New</span>
        </button>

        <button
          onClick={openSaveModal}
          disabled={isSaving}
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors disabled:opacity-50"
        >
          {isSaving ? <Loader size={13} className="animate-spin" /> : <Save size={13} />}
          <span className="hidden sm:block">Save</span>
        </button>

        {saveAsMode ? (
          <input
            ref={saveAsInputRef}
            value={saveAsName}
            onChange={(e) => setSaveAsName(e.target.value)}
            onBlur={commitSaveAs}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitSaveAs()
              if (e.key === 'Escape') setSaveAsMode(false)
            }}
            className="text-xs bg-slate-800 border border-indigo-500 rounded-lg px-2.5 py-1.5 text-slate-100 w-44 focus:outline-none"
            placeholder="New workflow name…"
          />
        ) : (
          <button
            onClick={enterSaveAs}
            disabled={isSaving}
            className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-3 py-1.5 rounded-lg border border-slate-700/50 transition-colors disabled:opacity-50"
            title="Save a copy with a new name"
          >
            <BookmarkPlus size={13} />
            <span className="hidden sm:block">Save As</span>
          </button>
        )}

        {isExecuting ? (
          <button
            onClick={stopExecution}
            className="flex items-center gap-1.5 text-xs bg-red-700/30 hover:bg-red-700/50 text-red-300 border border-red-700/50 px-3 py-1.5 rounded-lg transition-colors"
          >
            <Square size={13} />
            <span>Stop</span>
          </button>
        ) : (
          <div className="relative flex items-stretch">
            <button
              onClick={() => runExecution()}
              className="flex items-center gap-1.5 text-xs bg-green-700/30 hover:bg-green-600/40 text-green-300 border border-green-700/50 px-3 py-1.5 rounded-l-lg transition-colors font-medium"
              title="Run with default trigger"
            >
              <Play size={13} />
              <span>Run</span>
            </button>
            <button
              onClick={() => setShowRunMenu((v) => !v)}
              className="flex items-center text-xs bg-green-700/30 hover:bg-green-600/40 text-green-300 border-y border-r border-green-700/50 px-1.5 rounded-r-lg transition-colors"
              title="Run with…"
            >
              <ChevronDown size={13} />
            </button>

            {showRunMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowRunMenu(false)} />
                <div className="absolute top-full right-0 mt-1 w-72 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-50 overflow-hidden">
                  <div className="px-3 py-2 border-b border-slate-700">
                    <p className="text-[11px] text-slate-400 uppercase tracking-wide">Run with simulated trigger</p>
                  </div>

                  {/* Manual / built-in choices */}
                  <div className="py-1">
                    {['manual', 'webhook', 'cron', 'google_sheet', 'email'].map((tt) => {
                      const Icon = TRIGGER_RUN_ICONS[tt]
                      return (
                        <button
                          key={tt}
                          onClick={() => runWith({ triggerType: tt, payload: TRIGGER_DEFAULT_PAYLOADS[tt] })}
                          className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-200 hover:bg-slate-700/60 transition-colors text-left"
                        >
                          <Icon size={12} className="text-slate-400 flex-shrink-0" />
                          <span className="flex-1">{TRIGGER_RUN_LABELS[tt]}</span>
                          <span className="text-[9px] text-slate-500">simulated</span>
                        </button>
                      )
                    })}
                  </div>

                  {/* Saved triggers from this workflow's Start node */}
                  {configuredTriggers.length > 0 && (
                    <>
                      <div className="px-3 py-1.5 border-t border-slate-700 bg-slate-900/40">
                        <p className="text-[10px] text-slate-500 uppercase tracking-wide">Configured triggers</p>
                      </div>
                      <div className="py-1 max-h-44 overflow-y-auto">
                        {configuredTriggers.map((t) => {
                          const Icon = TRIGGER_RUN_ICONS[t.type] || Play
                          return (
                            <button
                              key={t.id}
                              onClick={() => runWith({
                                triggerType: t.type,
                                triggerId: t.id,
                                payload: TRIGGER_DEFAULT_PAYLOADS[t.type] || {},
                              })}
                              className="w-full flex items-center gap-2 px-3 py-2 text-xs text-slate-200 hover:bg-slate-700/60 transition-colors text-left"
                              disabled={t.enabled === false}
                            >
                              <Icon size={12} className="text-indigo-300 flex-shrink-0" />
                              <span className="flex-1 truncate">{t.name || TRIGGER_RUN_LABELS[t.type]}</span>
                              <span className="text-[9px] text-slate-500">{t.type}</span>
                              {t.enabled === false && <span className="text-[9px] text-amber-400">off</span>}
                            </button>
                          )
                        })}
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </div>
        )}
      </div>

      {/* Notification toast */}
      {notification && (
        <div
          className={`fixed top-16 right-4 z-50 px-4 py-2.5 rounded-xl text-sm font-medium shadow-2xl border transition-all ${
            notification.type === 'success'
              ? 'bg-green-900/90 text-green-200 border-green-700'
              : 'bg-red-900/90 text-red-200 border-red-700'
          }`}
        >
          {notification.type === 'success' ? '✓ ' : '✗ '}{notification.message}
        </div>
      )}

      {/* Close workflow dropdown on outside click */}
      {showWorkflows && (
        <div className="fixed inset-0 z-40" onClick={() => setShowWorkflows(false)} />
      )}

      {/* Save workflow modal */}
      <SaveWorkflowModal />

      {/* Delete confirmation modal */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60" onClick={() => setDeleteTarget(null)} />
          <div className="relative bg-slate-800 border border-slate-700 rounded-xl shadow-2xl p-5 w-80">
            <p className="text-sm font-semibold text-slate-100 mb-1">Delete Workflow</p>
            <p className="text-xs text-slate-400 mb-4">
              Delete <span className="text-slate-200 font-medium">"{deleteTarget.name}"</span>? This cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setDeleteTarget(null)}
                className="px-3 py-1.5 text-xs text-slate-300 hover:text-slate-100 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={() => { deleteWorkflow(deleteTarget.id); setDeleteTarget(null) }}
                className="px-3 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-500 rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  )
}
