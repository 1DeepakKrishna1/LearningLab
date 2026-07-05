const BASE = ''  // Vite proxy handles routing

export async function fetchWorkflows() {
  const r = await fetch(`${BASE}/workflows`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchWorkflow(id) {
  const r = await fetch(`${BASE}/workflows/${id}`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function executeWorkflow(workflowId, mode, initialInputs = null) {
  const body = { mode }
  if (initialInputs) body.initial_inputs = initialInputs
  const r = await fetch(`${BASE}/workflows/${workflowId}/execute`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function provideInput(executionId, nodeId, inputData) {
  const r = await fetch(`${BASE}/execution/${executionId}/input`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ node_id: nodeId, input_data: inputData }),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function resumeExecution(executionId) {
  const r = await fetch(`${BASE}/execution/${executionId}/resume`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  })
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}

export async function fetchStatus(executionId) {
  const r = await fetch(`${BASE}/execution/${executionId}/status`)
  if (!r.ok) throw new Error(await r.text())
  return r.json()
}
