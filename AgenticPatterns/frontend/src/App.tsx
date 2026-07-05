import { useEffect, useState, useCallback } from 'react'
import type { Pattern, ChatMessage } from './types'
import { fetchPatterns, runPattern } from './api'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import InputForm from './components/InputForm'
import './App.css'

let msgCounter = 0
function uid() {
  return String(++msgCounter)
}

export default function App() {
  const [patterns, setPatterns] = useState<Pattern[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  // Load pattern metadata from API
  useEffect(() => {
    fetchPatterns()
      .then(setPatterns)
      .catch((e: unknown) =>
        setLoadError(e instanceof Error ? e.message : 'Failed to load patterns'),
      )
  }, [])

  const selectedPattern = patterns.find((p) => p.id === selectedId) ?? null

  const handleSelect = useCallback((id: number) => {
    setSelectedId(id)
  }, [])

  const handleSubmit = useCallback(
    async (inputs: Record<string, unknown>) => {
      if (!selectedPattern || isLoading) return

      const userMsg: ChatMessage = {
        id: uid(),
        role: 'user',
        content: JSON.stringify(inputs),
        patternId: selectedPattern.id,
        patternName: selectedPattern.name,
        timestamp: new Date(),
      }

      const loadingMsg: ChatMessage = {
        id: uid(),
        role: 'assistant',
        content: '',
        patternId: selectedPattern.id,
        patternName: selectedPattern.name,
        timestamp: new Date(),
        isLoading: true,
      }

      setMessages((prev) => [...prev, userMsg, loadingMsg])
      setIsLoading(true)

      try {
        const data = await runPattern(selectedPattern.id, inputs)

        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? {
                  ...m,
                  isLoading: false,
                  result: data.result,
                  content: '',
                }
              : m,
          ),
        )
      } catch (e: unknown) {
        const errText = e instanceof Error ? e.message : 'Unknown error'
        setMessages((prev) =>
          prev.map((m) =>
            m.id === loadingMsg.id
              ? { ...m, isLoading: false, role: 'error' as const, content: errText }
              : m,
          ),
        )
      } finally {
        setIsLoading(false)
      }
    },
    [selectedPattern, isLoading],
  )

  if (loadError) {
    return (
      <div className="app-error">
        <div className="app-error-box">
          <h1>Cannot connect to API</h1>
          <p>{loadError}</p>
          <p className="app-error-hint">
            Start the FastAPI server with:
            <code>uvicorn api.main:app --reload --port 8000</code>
          </p>
          <button onClick={() => window.location.reload()}>Retry</button>
        </div>
      </div>
    )
  }

  return (
    <div className="app">
      {/* Mobile sidebar toggle */}
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen((o) => !o)}
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? '✕' : '☰'}
      </button>

      {/* Sidebar */}
      <div className={`sidebar-wrapper ${sidebarOpen ? 'sidebar-wrapper--open' : ''}`}>
        <Sidebar patterns={patterns} selectedId={selectedId} onSelect={handleSelect} />
      </div>

      {/* Main area */}
      <main className="main">
        <div className="chat-area">
          <ChatWindow messages={messages} />
        </div>

        {selectedPattern ? (
          <div className="form-area">
            <InputForm
              pattern={selectedPattern}
              onSubmit={handleSubmit}
              isLoading={isLoading}
            />
          </div>
        ) : (
          <div className="form-placeholder">
            <span>← Select a pattern from the sidebar to begin</span>
          </div>
        )}
      </main>
    </div>
  )
}
