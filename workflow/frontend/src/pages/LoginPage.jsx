import { useState } from 'react'
import { Eye, EyeOff, LogIn, CheckCircle2 } from 'lucide-react'
import useAuthStore from '../store/authStore'
import usePortalStore from '../store/portalStore'
import ThemeSwitcher from '../components/ThemeSwitcher'

const DEMO_CREDENTIALS = [
  { label: 'Product Admin',  user: 'admin',         password: 'Admin@123', color: 'purple' },
  { label: 'Process Admin',  user: 'processadmin',  password: 'Admin@123', color: 'blue' },
  { label: 'Org User',       user: 'alice',         password: 'User@123',  color: 'green' },
  { label: 'Customer Admin', user: 'custadmin',     password: 'Admin@123', color: 'cyan' },
  { label: 'Customer User',  user: 'custuser',      password: 'User@123',  color: 'teal' },
]

const FEATURES = [
  'Orchestrate complex multi-agent workflows visually',
  'Real-time execution monitoring and audit trails',
  'Role-based access control across teams and customers',
]

const colorMap = {
  purple: 'bg-purple-500/10 border-purple-500/30 text-purple-300',
  blue:   'bg-blue-500/10 border-blue-500/30 text-blue-300',
  green:  'bg-emerald-500/10 border-emerald-500/30 text-emerald-300',
  cyan:   'bg-cyan-500/10 border-cyan-500/30 text-cyan-300',
  teal:   'bg-teal-500/10 border-teal-500/30 text-teal-300',
}

const badgeMap = {
  purple: 'bg-purple-500/20 text-purple-300',
  blue:   'bg-blue-500/20 text-blue-300',
  green:  'bg-emerald-500/20 text-emerald-300',
  cyan:   'bg-cyan-500/20 text-cyan-300',
  teal:   'bg-teal-500/20 text-teal-300',
}

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  const { login, isLoading, error } = useAuthStore()
  const { setAppView, org } = usePortalStore()

  const demoCredentials = DEMO_CREDENTIALS.map((c) => ({
    ...c,
    email: `${c.user}@${org.domain || 'incepta.com'}`,
  }))

  async function handleSubmit(e) {
    e.preventDefault()
    const ok = await login(email, password)
    if (ok) setAppView('landing')
  }

  function fillCredentials(cred) {
    setEmail(cred.email)
    setPassword(cred.password)
  }

  return (
    <div className="flex h-screen w-screen overflow-hidden relative">
      {/* Theme switcher — top-right corner */}
      <div className="absolute top-4 right-4 z-20">
        <ThemeSwitcher />
      </div>

      {/* Left panel — branded hero */}
      <div className="login-panel-dark hidden lg:flex w-[60%] flex-col justify-between p-12 bg-gradient-to-br from-indigo-900 via-indigo-950 to-slate-900 relative overflow-hidden">
        {/* Background decoration */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-indigo-600/10 blur-3xl" />
          <div className="absolute top-1/2 -right-24 w-80 h-80 rounded-full bg-violet-600/10 blur-3xl" />
          <div className="absolute -bottom-24 left-1/3 w-72 h-72 rounded-full bg-indigo-500/8 blur-3xl" />
        </div>

        {/* Logo area */}
        <div className="relative z-10 flex items-center gap-3">
          {org.hasLogo && org.logoUrl && (
            <img
              src={org.logoUrl}
              alt={org.name}
              className="h-10 w-10 object-contain"
              onError={(e) => { e.target.style.display = 'none' }}
            />
          )}
          <span className="text-2xl font-bold text-white tracking-tight">{org.name}</span>
        </div>

        {/* Center content */}
        <div className="relative z-10 flex flex-col gap-8">
          <div>
            <h1 className="text-4xl font-extrabold text-white leading-tight mb-3">
              Intelligent Workflow<br />Orchestration
            </h1>
            <p className="text-indigo-300 text-lg leading-relaxed max-w-md">
              Design, deploy, and monitor enterprise-grade AI workflows with unprecedented clarity and control.
            </p>
          </div>

          <ul className="flex flex-col gap-4">
            {FEATURES.map((feature) => (
              <li key={feature} className="flex items-start gap-3">
                <CheckCircle2 className="text-indigo-400 mt-0.5 shrink-0" size={18} />
                <span className="text-slate-200 text-sm leading-relaxed">{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Bottom attribution */}
        <div className="relative z-10">
          <p className="text-slate-500 text-xs">Powered by {org.name} AI Platform &copy; 2026</p>
        </div>
      </div>

      {/* Right panel — login form */}
      <div className="flex-1 flex flex-col justify-center items-center bg-slate-950 px-6 py-10 overflow-y-auto">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="flex lg:hidden items-center gap-2 justify-center mb-8">
            {org.hasLogo && org.logoUrl && (
              <img
                src={org.logoUrl}
                alt={org.name}
                className="h-8 w-8 object-contain"
                onError={(e) => { e.target.style.display = 'none' }}
              />
            )}
            <span className="text-xl font-bold text-white">{org.name}</span>
          </div>

          <h2 className="text-2xl font-bold text-slate-100 mb-1">Welcome back</h2>
          <p className="text-slate-400 text-sm mb-8">Sign in to your workspace</p>

          {/* Login form */}
          <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Email
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
                className="bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                Password
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 pr-10 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-2.5">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="mt-1 flex items-center justify-center gap-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold rounded-lg px-4 py-2.5 text-sm transition-colors"
            >
              {isLoading ? (
                <>
                  <span className="inline-block h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                  Signing in…
                </>
              ) : (
                <>
                  <LogIn size={15} />
                  Sign In
                </>
              )}
            </button>
          </form>

          {/* Demo credentials */}
          
          <div className="mt-8">
            <p className="text-xs font-medium text-slate-500 uppercase tracking-wider mb-3">
              Demo Accounts — click to fill
            </p>
            <div className="flex flex-col gap-2">
              {demoCredentials.map((cred) => (
                <button
                  key={cred.email}
                  type="button"
                  onClick={() => fillCredentials(cred)}
                  className={`text-left w-full border rounded-lg px-4 py-3 transition-colors hover:brightness-110 ${colorMap[cred.color]}`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-slate-200">{cred.label}</span>
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${badgeMap[cred.color]}`}>
                      {cred.label}
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 font-mono leading-tight">
                    <span>{cred.email}</span>
                    <span className="mx-1 text-slate-600">/</span>
                    <span>{cred.password}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
          
        </div>
      </div>
    </div>
  )
}
