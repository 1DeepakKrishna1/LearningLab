import React, { useState } from 'react'
import { ChevronDown, ChevronUp, Database } from 'lucide-react'
import useStore from '../store/workflowStore'

const STATUS_STYLES = {
  completed: 'text-green-400 bg-green-900/20 border-green-700/40',
  failed:    'text-red-400 bg-red-900/20 border-red-700/40',
  running:   'text-blue-400 bg-blue-900/20 border-blue-700/40',
  pending:   'text-slate-400 bg-slate-800/40 border-slate-700/30',
  skipped:   'text-slate-500 bg-slate-900/20 border-slate-700/20',
}

const STATUS_ICONS = {
  completed: '✓',
  failed:    '✗',
  running:   '▶',
  pending:   '○',
  skipped:   '⏭',
}

export default function ExecutionPanel() {
  const {
    isExecPanelOpen, toggleExecPanel,
    executionSteps, executionCurrentStep,
    executionStatus, isExecuting, stopExecution,
    executionDataModelInstance,
  } = useStore()
  const [dmOpen, setDmOpen] = useState(false)

  if (!isExecPanelOpen && executionStatus === null) return null

  const totalMs = executionSteps.reduce((sum, s) => sum + (s.duration_ms || 0), 0)
  const completedSteps = executionSteps.filter((s) => ['completed', 'failed', 'skipped'].includes(s.status))
  const hasDmInstance = executionDataModelInstance && Object.keys(executionDataModelInstance).length > 0

  return (
    <div
      className={`border-t border-slate-800 bg-slate-900 flex flex-col transition-all ${
        isExecPanelOpen ? (hasDmInstance && dmOpen ? 'h-80' : 'h-52') : 'h-10'
      }`}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 h-10 flex-shrink-0 cursor-pointer" onClick={toggleExecPanel}>
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-300">Execution Log</span>
          {isExecuting && (
            <span className="text-[10px] bg-blue-900/40 text-blue-300 border border-blue-700/40 px-2 py-0.5 rounded-full animate-pulse">
              Running…
            </span>
          )}
          {executionStatus === 'completed' && !isExecuting && (
            <span className="text-[10px] bg-green-900/40 text-green-300 border border-green-700/40 px-2 py-0.5 rounded-full">
              ✓ Completed — {(totalMs / 1000).toFixed(1)}s
            </span>
          )}
          {executionStatus === 'failed' && !isExecuting && (
            <span className="text-[10px] bg-red-900/40 text-red-300 border border-red-700/40 px-2 py-0.5 rounded-full">
              ✗ Failed
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isExecuting && (
            <button
              onClick={(e) => { e.stopPropagation(); stopExecution() }}
              className="text-[11px] text-red-400 hover:text-red-300 px-2 py-0.5 rounded border border-red-800/50 hover:bg-red-900/20 transition-colors"
            >
              Stop
            </button>
          )}
          {isExecPanelOpen ? (
            <ChevronDown size={14} className="text-slate-500" />
          ) : (
            <ChevronUp size={14} className="text-slate-500" />
          )}
        </div>
      </div>

      {/* Steps list */}
      {isExecPanelOpen && (
        <>
          <div className="flex-1 overflow-x-auto overflow-y-auto px-4 pb-3">
            {executionSteps.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-600 text-xs">
                Waiting for execution results…
              </div>
            ) : (
              <div className="flex gap-2 items-start min-w-max">
                {executionSteps.map((step, i) => {
                  const isCurrent = i === executionCurrentStep
                  const isReached = i <= executionCurrentStep
                  const st = isReached ? step.status : 'pending'
                  const styles = STATUS_STYLES[st] || STATUS_STYLES.pending
                  const hasInvokeInputs = Object.keys(step.invoke_inputs || {}).length > 0

                  return (
                    <div key={step.node_id} className="flex items-center gap-2">
                      <div
                        className={`flex-shrink-0 w-40 p-2.5 rounded-lg border transition-all text-xs ${styles} ${
                          isCurrent ? 'ring-1 ring-blue-500/40 scale-[1.02]' : ''
                        }`}
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <span className={`text-sm font-bold ${st === 'running' ? 'animate-pulse' : ''}`}>
                            {STATUS_ICONS[st] || '○'}
                          </span>
                          <span className="font-semibold truncate leading-tight">{step.agent_name}</span>
                        </div>
                        {step.duration_ms > 0 && (
                          <div className="text-[10px] opacity-70">{step.duration_ms}ms</div>
                        )}
                        {st === 'completed' && step.output && (
                          <div className="text-[9px] opacity-60 mt-0.5 truncate">
                            {Object.entries(step.output).slice(0, 1).map(([k, v]) => `${k}: ${v}`).join('')}
                          </div>
                        )}
                        {hasInvokeInputs && (
                          <div className="text-[9px] text-violet-400/70 mt-0.5">
                            ⚡ {Object.keys(step.invoke_inputs).length} invoke param{Object.keys(step.invoke_inputs).length !== 1 ? 's' : ''}
                          </div>
                        )}
                      </div>
                      {i < executionSteps.length - 1 && (
                        <div className={`h-px w-4 flex-shrink-0 ${isReached ? 'bg-slate-500' : 'bg-slate-700'}`} />
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* Data model instance viewer (shown after completion) */}
          {hasDmInstance && executionStatus !== 'running' && (
            <div className="border-t border-slate-800 flex-shrink-0">
              <button
                onClick={() => setDmOpen(o => !o)}
                className="w-full flex items-center justify-between px-4 py-1.5 text-[11px] text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Database size={11} className="text-violet-400" />
                  Data Model Instance
                  <span className="text-[9px] bg-violet-900/40 text-violet-400 border border-violet-700/30 rounded-full px-1.5 py-0.5">
                    {Object.keys(executionDataModelInstance).length} entit{Object.keys(executionDataModelInstance).length !== 1 ? 'ies' : 'y'}
                  </span>
                </span>
                {dmOpen ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
              </button>
              {dmOpen && (
                <div className="px-4 pb-3 max-h-28 overflow-y-auto">
                  <pre className="text-[10px] text-violet-300 bg-violet-900/10 border border-violet-700/20 rounded p-2 whitespace-pre-wrap">
                    {JSON.stringify(executionDataModelInstance, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  )
}
