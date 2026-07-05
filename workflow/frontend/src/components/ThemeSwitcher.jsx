import React, { useState } from 'react'
import { Palette, Check } from 'lucide-react'
import { THEMES } from '../themes'
import useStore from '../store/workflowStore'

export default function ThemeSwitcher() {
  const { theme, setTheme } = useStore()
  const [open, setOpen] = useState(false)
  const current = THEMES.find((t) => t.id === theme) || THEMES[0]

  return (
    <div className="relative">
      {/* Trigger button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-700/50 px-2.5 py-1.5 rounded-lg border border-slate-700/50 transition-colors"
        title="Change theme"
      >
        <Palette size={13} />
        <span
          className="w-3 h-3 rounded-full flex-shrink-0"
          style={{ backgroundColor: current.swatches[2] }}
        />
      </button>

      {/* Dropdown */}
      {open && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setOpen(false)}
          />
          <div className="absolute top-full right-0 mt-2 z-50 w-64 rounded-2xl border border-slate-700 shadow-2xl overflow-hidden bg-slate-800">
            <div className="px-3 py-2.5 border-b border-slate-700">
              <p className="text-[11px] font-semibold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <Palette size={11} />
                UI Theme
              </p>
            </div>

            <div className="p-2 grid grid-cols-2 gap-2">
              {THEMES.map((t) => {
                const isActive = t.id === theme
                return (
                  <button
                    key={t.id}
                    onClick={() => { setTheme(t.id); setOpen(false) }}
                    className={`group relative flex flex-col items-start p-2.5 rounded-xl border transition-all text-left ${
                      isActive
                        ? 'border-2 scale-[1.02]'
                        : 'border-slate-700/60 hover:border-slate-500 hover:scale-[1.01]'
                    }`}
                    style={{
                      backgroundColor: t.swatches[0],
                      borderColor: isActive ? t.swatches[2] : undefined,
                    }}
                  >
                    {/* Swatches */}
                    <div className="flex gap-1 mb-2">
                      {t.swatches.map((s, i) => (
                        <div
                          key={i}
                          className="rounded-full border border-white/10"
                          style={{
                            width: i === 2 ? 14 : 10,
                            height: i === 2 ? 14 : 10,
                            backgroundColor: s,
                          }}
                        />
                      ))}
                    </div>

                    {/* Name */}
                    <span
                      className="text-[11px] font-semibold leading-tight"
                      style={{ color: t.id === 'light' ? '#0f172a' : '#e2e8f0' }}
                    >
                      {t.name}
                    </span>
                    <span
                      className="text-[9px] leading-tight mt-0.5"
                      style={{ color: t.id === 'light' ? '#64748b' : '#94a3b8' }}
                    >
                      {t.description}
                    </span>

                    {/* Active check */}
                    {isActive && (
                      <span
                        className="absolute top-1.5 right-1.5 w-4 h-4 rounded-full flex items-center justify-center"
                        style={{ backgroundColor: t.swatches[2] }}
                      >
                        <Check size={9} className="text-white" />
                      </span>
                    )}
                  </button>
                )
              })}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
