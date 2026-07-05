import type { Pattern } from './types'

const BASE = '/api'

export async function fetchPatterns(): Promise<Pattern[]> {
  const res = await fetch(`${BASE}/patterns`)
  if (!res.ok) throw new Error('Failed to fetch patterns')
  const data = await res.json()
  return data.patterns as Pattern[]
}

export async function runPattern(
  patternId: number,
  inputs: Record<string, unknown>,
): Promise<{ pattern_id: number; result: Record<string, unknown> }> {
  const res = await fetch(`${BASE}/patterns/${patternId}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(inputs),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error((err as { detail?: string }).detail ?? 'Pattern execution failed')
  }
  return res.json()
}
