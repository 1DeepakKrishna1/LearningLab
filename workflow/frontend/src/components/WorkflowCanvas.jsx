import React, { useCallback, useRef, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  BackgroundVariant,
} from 'reactflow'
import AgentNode from './nodes/AgentNode'
import ToolNode from './nodes/ToolNode'
import useStore from '../store/workflowStore'

const nodeTypes = { agentNode: AgentNode, toolNode: ToolNode }

export default function WorkflowCanvas() {
  const wrapperRef = useRef(null)
  const rfInstance = useRef(null)
  const [labelInput, setLabelInput] = useState('')

  const {
    nodes, edges,
    onNodesChange, onEdgesChange, onConnect,
    addNode, addToolNode, setSelectedNode, selectedNode,
    pendingConnection, confirmConnection, cancelConnection,
  } = useStore()

  const handleConfirm = useCallback(() => {
    confirmConnection(labelInput.trim())
    setLabelInput('')
  }, [confirmConnection, labelInput])

  const handleCancel = useCallback(() => {
    cancelConnection()
    setLabelInput('')
  }, [cancelConnection])

  const onInit = useCallback((instance) => {
    rfInstance.current = instance
  }, [])

  const onNodeClick = useCallback((_, node) => {
    setSelectedNode(node)
  }, [setSelectedNode])

  const onPaneClick = useCallback(() => {
    setSelectedNode(null)
  }, [setSelectedNode])

  const onDragOver = useCallback((event) => {
    event.preventDefault()
    event.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback((event) => {
    event.preventDefault()
    const bounds = wrapperRef.current?.getBoundingClientRect()
    if (!bounds || !rfInstance.current) return

    const position = rfInstance.current.project({
      x: event.clientX - bounds.left,
      y: event.clientY - bounds.top,
    })

    const agentRaw = event.dataTransfer.getData('application/reactflow-agent')
    if (agentRaw) {
      addNode(JSON.parse(agentRaw), position)
      return
    }

    const toolRaw = event.dataTransfer.getData('application/reactflow-tool')
    if (toolRaw) {
      addToolNode(JSON.parse(toolRaw), position)
    }
  }, [addNode, addToolNode])

  return (
    <div ref={wrapperRef} className="flex-1 h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onInit={onInit}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        onDrop={onDrop}
        onDragOver={onDragOver}
        fitView
        deleteKeyCode="Delete"
        defaultEdgeOptions={{ type: 'smoothstep', animated: false }}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#1e293b"
        />
        <Controls className="!bottom-6 !left-6" />
        <MiniMap
          className="!bottom-6 !right-6"
          nodeColor={(n) => {
            if (n.type === 'toolNode') {
              const toolColors = {
                api_call: '#0ea5e9', data_transform: '#14b8a6', notification: '#f59e0b',
                database: '#a855f7', file_io: '#f97316', ai_inference: '#ec4899',
                approval: '#f43f5e', webhook: '#06b6d4',
              }
              return toolColors[n.data?.toolType] || '#0ea5e9'
            }
            const colors = {
              start: '#22c55e', end: '#f43f5e', automatic: '#6366f1',
              role_based: '#10b981', human_in_the_loop: '#f59e0b',
              human_review: '#0ea5e9',
              conditional: '#f97316', parallel: '#a855f7',
            }
            return colors[n.data?.type] || '#6366f1'
          }}
          maskColor="rgba(15,23,42,0.7)"
        />
      </ReactFlow>

      {/* Edge label modal */}
      {pendingConnection && (
        <div className="absolute inset-0 flex items-center justify-center z-50">
          <div className="absolute inset-0 bg-black/30" onClick={handleCancel} />
          <div className="relative bg-slate-800 border border-slate-600 rounded-xl shadow-2xl p-4 w-72">
            <p className="text-xs font-semibold text-slate-100 mb-0.5">Label this connection</p>
            <p className="text-[10px] text-slate-500 mb-3 truncate">
              {pendingConnection.sourceName} → {pendingConnection.targetName}
            </p>
            <input
              autoFocus
              type="text"
              placeholder="e.g. on success, if approved… (optional)"
              value={labelInput}
              onChange={(e) => setLabelInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleConfirm()
                if (e.key === 'Escape') handleCancel()
              }}
              className="w-full bg-slate-700 border border-slate-600 rounded px-3 py-1.5 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors mb-3"
            />
            <div className="flex gap-2">
              <button
                onClick={handleConfirm}
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium py-1.5 rounded transition-colors"
              >
                Add Connection
              </button>
              <button
                onClick={handleCancel}
                className="flex-1 bg-slate-700 hover:bg-slate-600 text-slate-300 text-xs py-1.5 rounded transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {nodes.length === 0 && (
        <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none select-none">
          <div className="text-6xl mb-4 opacity-20">⚡</div>
          <p className="text-slate-500 text-lg font-medium">Drop agents or tools here to build your workflow</p>
          <p className="text-slate-600 text-sm mt-1">Drag from the left panel or clone a library template</p>
        </div>
      )}
    </div>
  )
}
