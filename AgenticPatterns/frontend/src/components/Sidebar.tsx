import { useMemo } from 'react'
import type { Pattern, PatternCategory } from '../types'
import './Sidebar.css'

interface Props {
  patterns: Pattern[]
  selectedId: number | null
  onSelect: (id: number) => void
}

const CATEGORY_ORDER: PatternCategory[] = ['Core', 'Extended', 'Advanced']

export default function Sidebar({ patterns, selectedId, onSelect }: Props) {
  const grouped = useMemo(() => {
    const map: Record<PatternCategory, Pattern[]> = { Core: [], Extended: [], Advanced: [] }
    patterns.forEach((p) => map[p.category].push(p))
    return map
  }, [patterns])

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <span className="sidebar-logo-icon">◈</span>
          <span className="sidebar-logo-text">Agentic Patterns</span>
        </div>
        <p className="sidebar-subtitle">21 AI Design Patterns</p>
      </div>

      <nav className="sidebar-nav">
        {CATEGORY_ORDER.map((cat) => (
          <div key={cat} className="sidebar-group">
            <div className="sidebar-group-label">{cat}</div>
            {grouped[cat].map((p) => (
              <button
                key={p.id}
                className={`sidebar-item ${selectedId === p.id ? 'sidebar-item--active' : ''}`}
                onClick={() => onSelect(p.id)}
                title={p.description}
              >
                <span className="sidebar-item-id">{String(p.id).padStart(2, '0')}</span>
                <span className="sidebar-item-name">{p.name}</span>
              </button>
            ))}
          </div>
        ))}
      </nav>
    </aside>
  )
}
