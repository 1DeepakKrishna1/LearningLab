import { useEffect, useRef, useCallback } from 'react'

/**
 * Opens an SSE stream at /events/{executionId} and calls onEvent(type, data)
 * for each received event. Automatically closes on unmount or when executionId
 * changes.
 *
 * When a terminal event (workflow_completed / workflow_failed) arrives the
 * EventSource is closed immediately from the client side.  This prevents the
 * subsequent server-side connection close from firing onerror — which would
 * otherwise look like a real network failure.
 */

const TERMINAL_EVENTS = new Set(['workflow_completed', 'workflow_failed'])

const ALL_EVENTS = [
  'connected',
  'workflow_started',
  'node_started',
  'awaiting_input',
  'node_completed',
  'awaiting_resume',
  'workflow_completed',
  'workflow_failed',
]

export function useSSE(executionId, onEvent) {
  const esRef        = useRef(null)
  const onEventRef   = useRef(onEvent)
  const intentional  = useRef(false)   // true when WE close, not the server
  onEventRef.current = onEvent

  const close = useCallback(() => {
    if (esRef.current) {
      intentional.current = true
      esRef.current.close()
      esRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!executionId) return

    // Reset flags for the new execution
    intentional.current = false
    close()

    const es = new EventSource(`/events/${executionId}`)
    esRef.current = es

    ALL_EVENTS.forEach(name => {
      es.addEventListener(name, e => {
        let data
        try { data = JSON.parse(e.data) } catch { data = e.data }

        // Deliver the event to the caller first
        onEventRef.current(name, data)

        // Then close cleanly so the server-side disconnect doesn't fire onerror
        if (TERMINAL_EVENTS.has(name)) {
          intentional.current = true
          es.close()
          esRef.current = null
        }
      })
    })

    es.onerror = () => {
      // Ignore errors that are a direct result of our own intentional close
      if (intentional.current) return
      onEventRef.current('_error', { message: 'SSE connection lost. Check server.' })
    }

    return close
  }, [executionId, close])

  return { close }
}
