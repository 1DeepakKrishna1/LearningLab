import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, XCircle, Info, X } from 'lucide-react'
import usePortalStore from '../../store/portalStore'

const TYPE_CONFIG = {
  success: {
    icon: CheckCircle2,
    bar: 'bg-emerald-500',
    iconCls: 'text-emerald-400',
    border: 'border-emerald-500/30',
    bg: 'bg-emerald-500/10',
    title: 'text-emerald-100',
  },
  error: {
    icon: XCircle,
    bar: 'bg-red-500',
    iconCls: 'text-red-400',
    border: 'border-red-500/30',
    bg: 'bg-red-500/10',
    title: 'text-red-100',
  },
  info: {
    icon: Info,
    bar: 'bg-blue-500',
    iconCls: 'text-blue-400',
    border: 'border-blue-500/30',
    bg: 'bg-blue-500/10',
    title: 'text-blue-100',
  },
}

// Duration that matches the store's setTimeout (3500ms)
const AUTO_DISMISS_MS = 3500

function Toast({ notification, onDismiss }) {
  const [visible, setVisible] = useState(false)
  const timerRef = useRef(null)

  // Slide in on mount
  useEffect(() => {
    // Next tick so the initial hidden state is painted first
    const raf = requestAnimationFrame(() => setVisible(true))

    // Auto-dismiss: start slide-out slightly before store clears it
    timerRef.current = setTimeout(() => {
      setVisible(false)
    }, AUTO_DISMISS_MS - 400)

    return () => {
      cancelAnimationFrame(raf)
      clearTimeout(timerRef.current)
    }
  }, [notification.id])

  function dismiss() {
    setVisible(false)
    clearTimeout(timerRef.current)
    // Let the slide-out animation finish before removing
    setTimeout(onDismiss, 300)
  }

  const cfg = TYPE_CONFIG[notification.type] ?? TYPE_CONFIG.info
  const Icon = cfg.icon

  return (
    <div
      role="alert"
      aria-live="assertive"
      style={{
        transform: visible ? 'translateX(0)' : 'translateX(calc(100% + 1.5rem))',
        opacity: visible ? 1 : 0,
        transition: 'transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.25s ease',
      }}
      className={[
        'flex items-start gap-3 w-80 max-w-[calc(100vw-2rem)]',
        'rounded-xl border shadow-2xl backdrop-blur-sm px-4 py-3',
        cfg.bg,
        cfg.border,
      ].join(' ')}
    >
      {/* Accent bar */}
      <div className={`absolute left-0 top-3 bottom-3 w-1 rounded-r-full ${cfg.bar}`} />

      {/* Icon */}
      <Icon size={18} className={`${cfg.iconCls} shrink-0 mt-0.5`} />

      {/* Message */}
      <p className={`flex-1 text-sm font-medium leading-snug ${cfg.title}`}>
        {notification.msg}
      </p>

      {/* Close button */}
      <button
        onClick={dismiss}
        className="text-slate-500 hover:text-slate-200 transition-colors shrink-0 mt-0.5 -mr-1"
        aria-label="Dismiss notification"
      >
        <X size={15} />
      </button>
    </div>
  )
}

export default function Notification() {
  const { notification } = usePortalStore()
  const [current, setCurrent] = useState(null)

  // Sync store notification into local state so we can animate out
  useEffect(() => {
    if (notification) {
      setCurrent(notification)
    }
    // Do NOT clear on null — let the animation run out naturally
  }, [notification])

  if (!current) return null

  return (
    <div
      className="fixed top-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
      aria-atomic="true"
    >
      <div className="pointer-events-auto relative">
        <Toast
          key={current.id}
          notification={current}
          onDismiss={() => setCurrent(null)}
        />
      </div>
    </div>
  )
}
