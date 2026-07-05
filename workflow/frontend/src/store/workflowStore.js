import { create } from 'zustand'

// Serialize a ReactFlow node to the backend WorkflowNode format
function _serializeNode(n) {
  if (n.type === 'toolNode') {
    return {
      id: n.id,
      node_kind: 'tool',
      agent_id: null,
      tool_id: n.data.toolId,
      position: n.position,
      data: {
        name: n.data.name,
        description: n.data.description,
        toolType: n.data.toolType,
        properties: n.data.properties || {},
      },
    }
  }
  return {
    id: n.id,
    node_kind: 'agent',
    agent_id: n.data.agentId,
    tool_id: null,
    position: n.position,
    data: {
      name: n.data.name,
      description: n.data.description,
      type: n.data.type,
      tools: n.data.tools,
      toolConfigs: n.data.toolConfigs || {},
      properties: n.data.properties,
      invoke: n.data.invoke || { input_parameters: [], output_parameters: [] },
    },
  }
}
import { addEdge, applyNodeChanges, applyEdgeChanges } from 'reactflow'
import * as api from '../api/api'
import { DEFAULT_THEME } from '../themes'

const useStore = create((set, get) => ({
  // ── Theme ─────────────────────────────────────────────
  theme: localStorage.getItem('wf-theme') || DEFAULT_THEME,

  setTheme: (theme) => {
    localStorage.setItem('wf-theme', theme)
    document.documentElement.setAttribute('data-theme', theme)
    set({ theme })
  },

  // ── Library data ──────────────────────────────────────
  libraryWorkflows: [],
  libraryAgents: [],
  tools: [],

  // ── User workspace ────────────────────────────────────
  userWorkflows: [],
  workflowId: null,
  workflowName: 'New Workflow',
  workflowDescription: '',

  // ── ReactFlow canvas ──────────────────────────────────
  nodes: [],
  edges: [],

  // ── Selection ─────────────────────────────────────────
  selectedNode: null,

  // ── Pending edge label ────────────────────────────────
  pendingConnection: null, // { connection, sourceName, targetName } | null

  // ── Execution ─────────────────────────────────────────
  isExecuting: false,
  executionSteps: [],
  executionCurrentStep: -1,
  executionStatus: null,   // null | 'running' | 'completed' | 'failed'
  executionDataModelInstance: null, // data model runtime state after completion
  isExecPanelOpen: false,
  humanInputPending: null, // { step, stepIndex, resume: fn } | null

  // ── AI Assistant ──────────────────────────────────────
  isAIOpen: false,
  aiMessages: [],
  isAILoading: false,

  // ── Data Models & Associations ────────────────────────
  dataModels: [],
  currentAssociation: null,
  isSaveModalOpen: false,

  // ── UI feedback ───────────────────────────────────────
  isSaving: false,
  isLoading: false,
  notification: null,

  // ── ReactFlow handlers ────────────────────────────────
  onNodesChange: (changes) =>
    set((s) => ({ nodes: applyNodeChanges(changes, s.nodes) })),

  onEdgesChange: (changes) =>
    set((s) => ({ edges: applyEdgeChanges(changes, s.edges) })),

  onConnect: (connection) => {
    const s = get()
    const sourceNode = s.nodes.find((n) => n.id === connection.source)
    const targetNode = s.nodes.find((n) => n.id === connection.target)

    if (sourceNode?.data?.type === 'end') {
      get()._notify('error', 'End agent cannot have outgoing connections')
      return
    }
    if (targetNode?.data?.type === 'start') {
      get()._notify('error', 'Start agent cannot receive incoming connections')
      return
    }

    // Queue the connection so the user can optionally add a label
    set({
      pendingConnection: {
        connection,
        sourceName: sourceNode?.data?.name || 'Agent',
        targetName: targetNode?.data?.name || 'Agent',
      },
    })
  },

  confirmConnection: (label) => {
    const { pendingConnection } = get()
    if (!pendingConnection) return
    const { connection } = pendingConnection
    set((st) => ({
      edges: addEdge(
        { ...connection, type: 'smoothstep', animated: false, label: label || undefined },
        st.edges
      ),
      pendingConnection: null,
    }))
  },

  cancelConnection: () => set({ pendingConnection: null }),

  // ── Node management ───────────────────────────────────
  setSelectedNode: (node) => set({ selectedNode: node }),

  addNode: (agentData, position) => {
    const { nodes } = get()

    // Enforce one-per-workflow constraint for Start and End
    if (agentData.type === 'start' && nodes.some((n) => n.data.type === 'start')) {
      get()._notify('error', 'Workflow can only have one Start agent')
      return
    }
    if (agentData.type === 'end' && nodes.some((n) => n.data.type === 'end')) {
      get()._notify('error', 'Workflow can only have one End agent')
      return
    }

    const newNode = {
      id: `node-${Date.now()}`,
      type: 'agentNode',
      position,
      data: {
        agentId: agentData.id,
        name: agentData.name,
        description: agentData.description,
        type: agentData.type,
        tools: agentData.tools || [],
        toolConfigs: { ...(agentData.tool_configs || {}) },
        color: agentData.color || '#6366f1',
        properties: { ...(agentData.properties || {}) },
        invoke: agentData.invoke
          ? { ...agentData.invoke }
          : { input_parameters: [], output_parameters: [] },
        executionStatus: null,
        executionResult: null,
      },
    }
    set((s) => ({ nodes: [...s.nodes, newNode] }))
  },

  addToolNode: (toolData, position) => {
    const newNode = {
      id: `node-${Date.now()}`,
      type: 'toolNode',
      position,
      data: {
        toolId: toolData.id,
        name: toolData.name,
        description: toolData.description,
        toolType: toolData.type,
        properties: { ...(toolData.properties || {}) },
        executionStatus: null,
        executionResult: null,
      },
    }
    set((s) => ({ nodes: [...s.nodes, newNode] }))
  },

  updateNodeData: (nodeId, patch) =>
    set((s) => ({
      nodes: s.nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...patch } } : n
      ),
      selectedNode:
        s.selectedNode?.id === nodeId
          ? { ...s.selectedNode, data: { ...s.selectedNode.data, ...patch } }
          : s.selectedNode,
    })),

  deleteNode: (nodeId) =>
    set((s) => ({
      nodes: s.nodes.filter((n) => n.id !== nodeId),
      edges: s.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNode: s.selectedNode?.id === nodeId ? null : s.selectedNode,
    })),

  // ── Load library data ─────────────────────────────────
  loadLibrary: async () => {
    try {
      const [workflows, agents, tools] = await Promise.all([
        api.getLibraryWorkflows(),
        api.getLibraryAgents(),
        api.getTools(),
      ])
      set({ libraryWorkflows: workflows, libraryAgents: agents, tools })
    } catch (err) {
      console.error('Failed to load library:', err)
    }
  },

  loadUserWorkflows: async () => {
    try {
      const workflows = await api.getWorkflows()
      set({ userWorkflows: workflows })
    } catch (err) {
      console.error('Failed to load user workflows:', err)
    }
  },

  // ── Load a specific workflow into canvas ──────────────
  loadWorkflow: async (id) => {
    try {
      set({ isLoading: true })
      const workflow = await api.getWorkflow(id)
      const agents = get().libraryAgents

      const rfNodes = workflow.nodes.map((node) => {
        if (node.node_kind === 'tool') {
          return {
            id: node.id,
            type: 'toolNode',
            position: node.position,
            data: {
              toolId: node.tool_id,
              name: node.data?.name || 'Tool',
              description: node.data?.description || '',
              toolType: node.data?.toolType || 'api_call',
              properties: node.data?.properties || {},
              executionStatus: null,
              executionResult: null,
            },
          }
        }
        const agent = agents.find((a) => a.id === node.agent_id) || {}
        return {
          id: node.id,
          type: 'agentNode',
          position: node.position,
          data: {
            agentId: node.agent_id,
            name: node.data?.name || agent.name || 'Agent',
            description: node.data?.description || agent.description || '',
            type: node.data?.type || agent.type || 'automatic',
            tools: node.data?.tools || agent.tools || [],
            toolConfigs: node.data?.toolConfigs || {},
            color: agent.color || '#6366f1',
            properties: node.data?.properties || agent.properties || {},
            invoke: node.data?.invoke || agent.invoke || { input_parameters: [], output_parameters: [] },
            executionStatus: null,
            executionResult: null,
          },
        }
      })

      const rfEdges = workflow.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || undefined,
        type: 'smoothstep',
        animated: false,
      }))

      set({
        workflowId: workflow.id,
        workflowName: workflow.name,
        workflowDescription: workflow.description,
        nodes: rfNodes,
        edges: rfEdges,
        selectedNode: null,
        executionStatus: null,
        executionSteps: [],
        executionCurrentStep: -1,
        isLoading: false,
      })

      // Load the association for this workflow (non-blocking)
      get().loadCurrentAssociation(workflow.id)
    } catch (err) {
      console.error('Failed to load workflow:', err)
      set({ isLoading: false })
    }
  },

  // ── Save workflow ─────────────────────────────────────
  saveWorkflow: async () => {
    const s = get()
    // Always open modal to allow association editing
    get().openSaveModal()
    return
  },

  // ── Direct save (used internally by execution auto-save) ─
  _directSave: async () => {
    try {
      set({ isSaving: true })
      const s = get()
      const payload = {
        name: s.workflowName,
        description: s.workflowDescription,
        nodes: s.nodes.map((n) => _serializeNode(n)),
        edges: s.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || null,
          type: e.type || 'smoothstep',
        })),
      }

      let saved
      if (s.workflowId) {
        saved = await api.updateWorkflow(s.workflowId, payload)
      } else {
        saved = await api.createWorkflow(payload)
        set({ workflowId: saved.id })
      }

      const workflows = await api.getWorkflows()
      set({ userWorkflows: workflows, isSaving: false })
      get()._notify('success', 'Workflow saved!')
    } catch (err) {
      console.error('Save failed:', err)
      set({ isSaving: false })
      get()._notify('error', 'Failed to save workflow')
    }
  },

  // ── Save current canvas as a new workflow ─────────────
  saveWorkflowAs: async (newName) => {
    try {
      set({ isSaving: true })
      const s = get()
      const payload = {
        name: newName || `${s.workflowName} (Copy)`,
        description: s.workflowDescription,
        nodes: s.nodes.map((n) => _serializeNode(n)),
        edges: s.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || null,
          type: e.type || 'smoothstep',
        })),
      }
      const saved = await api.createWorkflow(payload)
      const workflows = await api.getWorkflows()
      set({ workflowId: saved.id, workflowName: saved.name, userWorkflows: workflows, isSaving: false })
      get()._notify('success', `Saved as "${saved.name}"!`)
    } catch (err) {
      console.error('Save As failed:', err)
      set({ isSaving: false })
      get()._notify('error', 'Failed to save workflow copy')
    }
  },

  // ── Save modal controls ───────────────────────────────
  openSaveModal: () => set({ isSaveModalOpen: true }),
  closeSaveModal: () => set({ isSaveModalOpen: false }),

  // ── Load data models ──────────────────────────────────
  loadDataModels: async () => {
    try {
      const models = await api.getDataModels()
      set({ dataModels: models })
    } catch (err) {
      console.error('Failed to load data models:', err)
    }
  },

  // ── Load current association ──────────────────────────
  loadCurrentAssociation: async (workflowId) => {
    try {
      const assoc = await api.getWorkflowAssociation(workflowId)
      set({ currentAssociation: assoc || null })
    } catch {
      set({ currentAssociation: null })
    }
  },

  // ── Save workflow with association data ───────────────
  saveWithAssociation: async (workflowMeta, associationData) => {
    try {
      set({ isSaving: true, isSaveModalOpen: false })
      const s = get()

      const payload = {
        name: workflowMeta.name,
        description: workflowMeta.description,
        nodes: s.nodes.map((n) => _serializeNode(n)),
        edges: s.edges.map((e) => ({
          id: e.id,
          source: e.source,
          target: e.target,
          label: e.label || null,
          type: e.type || 'smoothstep',
        })),
      }

      let saved
      if (s.workflowId) {
        saved = await api.updateWorkflow(s.workflowId, payload)
      } else {
        saved = await api.createWorkflow(payload)
      }

      set({
        workflowId: saved.id,
        workflowName: saved.name,
        workflowDescription: saved.description,
      })

      // Only upsert if associationData is not null
      if (associationData !== null) {
        const assocPayload = { workflow_id: saved.id, ...associationData }
        const savedAssoc = await api.upsertAssociation(assocPayload)
        set({ currentAssociation: savedAssoc })
      }

      const workflows = await api.getWorkflows()
      set({ userWorkflows: workflows, isSaving: false })
      get()._notify('success', 'Workflow saved!')
    } catch (err) {
      console.error('Save with association failed:', err)
      set({ isSaving: false })
      get()._notify('error', 'Failed to save workflow')
    }
  },

  // ── Clone a library workflow ──────────────────────────
  cloneWorkflow: async (workflowId) => {
    try {
      const cloned = await api.cloneWorkflow(workflowId)
      const workflows = await api.getWorkflows()
      set({ userWorkflows: workflows })
      get()._notify('success', `"${cloned.name}" cloned!`)
      await get().loadWorkflow(cloned.id)
    } catch (err) {
      console.error('Clone failed:', err)
      get()._notify('error', 'Failed to clone workflow')
    }
  },

  // ── Delete a user workflow ────────────────────────────
  deleteWorkflow: async (id) => {
    try {
      await api.deleteWorkflow(id)
      const workflows = await api.getWorkflows()
      const isCurrent = get().workflowId === id
      set({ userWorkflows: workflows })
      if (isCurrent) get().newWorkflow()
      get()._notify('success', 'Workflow deleted')
    } catch (err) {
      console.error('Delete failed:', err)
      get()._notify('error', 'Failed to delete workflow')
    }
  },

  // ── New blank workflow ────────────────────────────────
  newWorkflow: () =>
    set({
      workflowId: null,
      workflowName: 'New Workflow',
      workflowDescription: '',
      nodes: [],
      edges: [],
      selectedNode: null,
      executionStatus: null,
      executionSteps: [],
      executionCurrentStep: -1,
      executionDataModelInstance: null,
      isExecPanelOpen: false,
      currentAssociation: null,
      isSaveModalOpen: false,
    }),

  // ── Run execution simulation ──────────────────────────
  // Optional `runOptions`:
  //   { triggerType: 'webhook'|'cron'|'google_sheet'|'email'|'manual',
  //     triggerId?: string,            // pick a saved trigger by id
  //     payload?: object }             // body sent through the trigger
  runExecution: async (runOptions = null) => {
    const s = get()
    if (s.nodes.length === 0) {
      get()._notify('error', 'Add some agents before running!')
      return
    }

    // Auto-save if needed
    if (!s.workflowId) await get()._directSave()
    const currentId = get().workflowId

    set({
      isExecuting: true,
      executionSteps: [],
      executionCurrentStep: -1,
      executionStatus: 'running',
      isExecPanelOpen: true,
    })

    // Set all nodes to pending
    set((st) => ({
      nodes: st.nodes.map((n) => ({
        ...n,
        data: { ...n.data, executionStatus: 'pending', executionResult: null },
      })),
    }))

    try {
      // If runOptions specifies a non-manual trigger, route through the
      // /triggers/simulate endpoint so the backend exercises the real trigger
      // handling code path (filters, secret checks bypassed since simulated).
      let result
      if (runOptions && runOptions.triggerType && runOptions.triggerType !== 'manual') {
        result = await api.simulateTrigger(currentId, {
          trigger_id: runOptions.triggerId || undefined,
          trigger_type: runOptions.triggerType,
          payload: runOptions.payload || {},
        })
      } else {
        result = await api.runExecution(currentId, runOptions?.payload ? {
          type: 'manual',
          name: 'Manual',
          payload: runOptions.payload,
        } : null)
      }
      set({
        executionSteps: [],
        executionDataModelInstance: result.data_model_instance || null,
      })
      // The backend produces a step result for every node; we walk the graph
      // and play only the path actually taken so branching agents follow a
      // single output flow (see pickBranch below).

      // Index backend step results by node id.
      const stepMap = {}
      result.steps.forEach((s) => { stepMap[s.node_id] = s })

      const edges = get().edges || []
      const nodeById = Object.fromEntries(get().nodes.map((n) => [n.id, n]))
      const outgoingEdges = (id) => edges.filter((e) => e.source === id)
      const isParallel = (id) => (nodeById[id]?.data?.type) === 'parallel'

      // Choose a single outgoing edge for a non-parallel branch, based on the
      // node's decision: the human judgment, or an automatic node's output
      // "branch"/"decision". Edge labels (e.g. Accept / Reject / Success) are
      // matched exactly first, then via positive/negative synonyms.
      const pickBranch = (decision, candidates) => {
        const norm = (v) => (v ?? '').toString().trim().toLowerCase()
        const d = norm(decision)
        if (d) {
          const exact = candidates.find((e) => norm(e.label) === d)
          if (exact) return exact
        }
        const POSITIVE = ['approve', 'accept', 'yes', 'true', 'success', 'pass', 'continue', 'proceed', 'ok']
        const NEGATIVE = ['reject', 'deny', 'no', 'false', 'fail', 'failed', 'decline', 'stop']
        if (POSITIVE.includes(d)) {
          const m = candidates.find((e) => POSITIVE.includes(norm(e.label)))
          if (m) return m
        }
        if (NEGATIVE.includes(d)) {
          const m = candidates.find((e) => NEGATIVE.includes(norm(e.label)))
          if (m) return m
        }
        if (d) {
          const partial = candidates.find(
            (e) => norm(e.label) && (norm(e.label).includes(d) || d.includes(norm(e.label)))
          )
          if (partial) return partial
        }
        return candidates[0] // no decision/label info → fall back to first edge
      }

      // Entry point: the Start agent, otherwise the first reported step.
      const startNode = get().nodes.find((n) => n.data?.type === 'start')
      const frontier = [startNode?.id || result.steps[0]?.node_id].filter(Boolean)
      const visited = new Set()
      // Status reflects only the path actually taken; a failure on the path
      // flips this via finish('failed') below.
      let finalStatus = 'completed'

      const finish = (status) => {
        set((st) => ({
          isExecuting: false,
          executionStatus: status,
          // Nodes never reached (untaken branches) are marked skipped.
          nodes: st.nodes.map((n) =>
            visited.has(n.id)
              ? n
              : { ...n, data: { ...n.data, executionStatus: 'skipped' } }
          ),
        }))
        get()._notify(
          status === 'completed' ? 'success' : 'error',
          status === 'completed' ? 'Execution completed!' : 'Execution failed'
        )
      }

      const visitNext = () => {
        while (frontier.length && visited.has(frontier[0])) frontier.shift()
        if (frontier.length === 0) { finish(finalStatus); return }

        const nodeId = frontier.shift()
        visited.add(nodeId)
        const step = stepMap[nodeId]
        if (!step) { visitNext(); return }

        // Append this step to the visible log and mark the node running.
        set((st) => {
          const nextSteps = [...st.executionSteps, step]
          return {
            executionSteps: nextSteps,
            executionCurrentStep: nextSteps.length - 1,
            nodes: st.nodes.map((n) =>
              n.id === nodeId
                ? { ...n, data: { ...n.data, executionStatus: 'running', executionResult: step } }
                : n
            ),
          }
        })

        const advance = (completedStep, decision) => {
          set((st) => ({
            executionSteps: st.executionSteps.map((s) =>
              s.node_id === nodeId ? completedStep : s
            ),
            nodes: st.nodes.map((n) =>
              n.id === nodeId
                ? { ...n, data: { ...n.data, executionStatus: completedStep.status, executionResult: completedStep } }
                : n
            ),
          }))

          if (completedStep.status === 'failed') { finish('failed'); return }

          // Decide which outgoing flow(s) to follow next.
          const outs = outgoingEdges(nodeId)
          let nextIds = []
          if (outs.length <= 1) {
            nextIds = outs.map((e) => e.target)          // linear: follow the single edge
          } else if (isParallel(nodeId)) {
            nextIds = outs.map((e) => e.target)          // parallel: fan out to every branch
          } else {
            const picked = pickBranch(decision, outs)    // branching: follow exactly one
            nextIds = picked ? [picked.target] : []
          }
          nextIds.forEach((id) => { if (!visited.has(id)) frontier.push(id) })
          setTimeout(visitNext, 700)
        }

        if (step.requires_human_input) {
          // Pause: show human input modal; the judgment selects the branch.
          set({
            humanInputPending: {
              step,
              resume: (humanResponse) => {
                const completedStep = {
                  ...step,
                  status: 'completed',
                  human_response: humanResponse,
                  output: {
                    judgment: humanResponse.judgment,
                    ...Object.fromEntries(
                      Object.entries(humanResponse.inputs).filter(([, v]) => v !== '')
                    ),
                  },
                  logs: [
                    ...step.logs,
                    `Judgment: ${humanResponse.judgment}`,
                    'Human review completed.',
                  ],
                }
                set({ humanInputPending: null })
                advance(completedStep, humanResponse.judgment)
              },
            },
          })
          return // paused — resumes via resume()
        }

        // Automatic node: reveal the result after a short delay.
        setTimeout(() => {
          const decision =
            step.output?.branch ?? step.output?.decision ?? step.output?.judgment ?? null
          advance(step, decision)
        }, 1000)
      }

      visitNext()
    } catch (err) {
      console.error('Execution failed:', err)
      set({ isExecuting: false, executionStatus: 'failed' })
      get()._notify('error', 'Execution failed')
    }
  },

  stopExecution: () => {
    set((s) => ({
      isExecuting: false,
      executionStatus: null,
      executionSteps: [],
      executionCurrentStep: -1,
      executionDataModelInstance: null,
      humanInputPending: null,
      nodes: s.nodes.map((n) => ({
        ...n,
        data: { ...n.data, executionStatus: null, executionResult: null },
      })),
    }))
  },

  submitHumanInput: (judgment, inputs) => {
    const { humanInputPending } = get()
    if (humanInputPending?.resume) {
      humanInputPending.resume({ judgment, inputs })
    }
  },

  // ── AI Assistant ──────────────────────────────────────
  toggleAI: () => set((s) => ({ isAIOpen: !s.isAIOpen })),

  sendAIMessage: async (message) => {
    const s = get()
    const userMsg = { role: 'user', content: message }
    set((st) => ({ aiMessages: [...st.aiMessages, userMsg], isAILoading: true }))

    try {
      const context = {
        name: s.workflowName,
        description: s.workflowDescription,
        agents: s.nodes.map((n) => ({ name: n.data.name, type: n.data.type })),
        connections: s.edges.length,
      }
      const response = await api.sendAIMessage(message, context, [...s.aiMessages, userMsg])
      set((st) => ({
        aiMessages: [...st.aiMessages, { role: 'assistant', content: response.message }],
        isAILoading: false,
      }))
    } catch {
      set((st) => ({
        aiMessages: [
          ...st.aiMessages,
          { role: 'assistant', content: 'Sorry, I hit an error. Please try again.' },
        ],
        isAILoading: false,
      }))
    }
  },

  // ── Helpers ───────────────────────────────────────────
  setWorkflowName: (name) => set({ workflowName: name }),
  setWorkflowDescription: (desc) => set({ workflowDescription: desc }),
  toggleExecPanel: () => set((s) => ({ isExecPanelOpen: !s.isExecPanelOpen })),

  _notify: (type, message) => {
    set({ notification: { type, message } })
    setTimeout(() => set({ notification: null }), 3500)
  },
}))

export default useStore
