import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { CheckCircle2, LogOut, Mail, ShieldCheck, Sparkles, UserRound, X } from 'lucide-react'
import { insforge, insforgeConfigured } from './insforge'

const AUTH_HINT = 'sports-zenith-auth-session'

const AuthContext = createContext({
  configured: false,
  loading: true,
  user: null,
  authConfig: null,
  refreshUser: async () => null,
  sendOtp: async () => ({ data: null, error: new Error('Auth unavailable') }),
  verifyOtp: async () => ({ data: null, error: new Error('Auth unavailable') }),
  signOut: async () => ({ error: null }),
  getAccessToken: async () => null,
})

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [authConfig, setAuthConfig] = useState(null)
  const [loading, setLoading] = useState(true)

  const refreshUser = useCallback(async () => {
    if (!insforgeConfigured || !insforge) {
      setUser(null)
      setLoading(false)
      return null
    }
    try {
      const { data, error } = await insforge.auth.getCurrentUser()
      if (error) {
        setUser(null)
        window.localStorage.removeItem(AUTH_HINT)
        return null
      }
      const next = data?.user || null
      setUser(next)
      if (next) window.localStorage.setItem(AUTH_HINT, '1')
      else window.localStorage.removeItem(AUTH_HINT)
      return next
    } catch {
      setUser(null)
      return null
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let active = true

    const load = async () => {
      if (!insforgeConfigured || !insforge) {
        if (active) setLoading(false)
        return
      }
      try {
        const { data: config } = await insforge.auth.getPublicAuthConfig()
        if (!active) return
        setAuthConfig(config || null)
        if (window.localStorage.getItem(AUTH_HINT) === '1') {
          await refreshUser()
        } else {
          setUser(null)
        }
      } catch {
        if (active) setUser(null)
      } finally {
        if (active) setLoading(false)
      }
    }

    load()
    const unsubscribe = insforgeConfigured && insforge
      ? insforge.auth.onAuthStateChange(() => { refreshUser() })
      : null

    return () => {
      active = false
      if (typeof unsubscribe === 'function') unsubscribe()
    }
  }, [refreshUser])

  const value = useMemo(() => ({
    configured: insforgeConfigured,
    loading,
    user,
    authConfig,
    refreshUser,
    sendOtp: async (email) => {
      if (!insforge) return { data: null, error: new Error('Account service is unavailable') }
      return insforge.auth.signInWithOtp({ email })
    },
    verifyOtp: async (email, otp, name) => {
      if (!insforge) return { data: null, error: new Error('Account service is unavailable') }
      const result = await insforge.auth.verifyOtp({ email, otp, ...(name ? { name } : {}) })
      if (!result.error) {
        window.localStorage.setItem(AUTH_HINT, '1')
        await refreshUser()
      }
      return result
    },
    signOut: async () => {
      if (!insforge) return { error: null }
      const result = await insforge.auth.signOut()
      window.localStorage.removeItem(AUTH_HINT)
      setUser(null)
      return result
    },
    getAccessToken: async () => {
      if (!insforge) return null
      try {
        return await insforge.getHttpClient().getValidAccessToken()
      } catch {
        return null
      }
    },
  }), [loading, user, authConfig, refreshUser])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}

function AccountModal({ onClose }) {
  const { configured, user, authConfig, sendOtp, verifyOtp, signOut } = useAuth()
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState(user?.email || '')
  const [name, setName] = useState(user?.profile?.name || '')
  const [otp, setOtp] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const close = (event) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [onClose])

  const requestCode = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await sendOtp(email.trim())
      if (result.error) throw result.error
      setStep('code')
      setMessage('Check your email for the sign-in code.')
    } catch (err) {
      setError(err?.message || 'Could not send a sign-in code.')
    } finally {
      setBusy(false)
    }
  }

  const verifyCode = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const result = await verifyOtp(email.trim(), otp.trim(), name.trim())
      if (result.error) throw result.error
      onClose()
    } catch (err) {
      setError(err?.message || 'That code could not be verified.')
    } finally {
      setBusy(false)
    }
  }

  const doSignOut = async () => {
    setBusy(true)
    await signOut()
    setBusy(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-slate-950/45 p-0 backdrop-blur-sm sm:items-center sm:p-5" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Sports Zenith account"
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md rounded-t-[30px] border border-slate-200 bg-white p-6 shadow-2xl sm:rounded-[30px]"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="text-xs font-black uppercase tracking-[0.16em] text-blue-700">Sports Zenith account</div>
            <div className="mt-1 text-2xl font-black tracking-tight text-slate-950">{user ? 'Your account' : 'Sign in'}</div>
          </div>
          <button type="button" aria-label="Close account dialog" onClick={onClose} className="flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 text-slate-500">
            <X size={18} />
          </button>
        </div>

        {!configured ? (
          <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold leading-6 text-amber-950">
            Account services are not configured in this build.
          </div>
        ) : user ? (
          <div className="mt-6">
            <div className="rounded-3xl border border-slate-200 bg-slate-50 p-5">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-lg font-black text-white">
                  {(user.profile?.name || user.email || 'S').slice(0, 1).toUpperCase()}
                </div>
                <div className="min-w-0">
                  <div className="truncate font-black text-slate-950">{user.profile?.name || 'Sports Zenith member'}</div>
                  <div className="truncate text-sm font-semibold text-slate-500">{user.email}</div>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs font-bold text-emerald-700">
                <CheckCircle2 size={15} /> {user.emailVerified ? 'Email verified' : 'Signed in'}
              </div>
            </div>
            <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-xs leading-5 text-blue-900">
              Private Survivor entries, connected fantasy leagues and account preferences will live behind this identity boundary.
            </div>
            <button type="button" disabled={busy} onClick={doSignOut} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-black text-slate-700 disabled:opacity-50">
              <LogOut size={16} /> Sign out
            </button>
          </div>
        ) : step === 'email' ? (
          <form onSubmit={requestCode} className="mt-6">
            <div className="rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-950">
              <div className="flex items-center gap-2 font-black"><ShieldCheck size={17} /> Passwordless sign-in</div>
              <div className="mt-1">We’ll email you a one-time code. New users can create an account through the same flow.</div>
            </div>

            <label className="mt-5 block text-xs font-black uppercase tracking-[0.12em] text-slate-500">Email</label>
            <div className="mt-2 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3">
              <Mail size={17} className="text-slate-400" />
              <input required type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="min-w-0 flex-1 bg-transparent py-3 text-sm font-semibold text-slate-900 outline-none" />
            </div>

            <label className="mt-4 block text-xs font-black uppercase tracking-[0.12em] text-slate-500">Display name <span className="normal-case tracking-normal text-slate-400">(optional)</span></label>
            <div className="mt-2 flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3">
              <UserRound size={17} className="text-slate-400" />
              <input autoComplete="name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Your name" className="min-w-0 flex-1 bg-transparent py-3 text-sm font-semibold text-slate-900 outline-none" />
            </div>

            {authConfig?.requireEmailVerification && (
              <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-400">Email verification is required for this account system.</div>
            )}
            {error && <div className="mt-4 rounded-xl bg-rose-50 p-3 text-xs font-bold text-rose-700">{error}</div>}
            <button disabled={busy || !email.trim()} className="mt-5 flex w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white disabled:opacity-40">
              <Sparkles size={16} /> {busy ? 'Sending…' : 'Email me a code'}
            </button>
          </form>
        ) : (
          <form onSubmit={verifyCode} className="mt-6">
            <div className="rounded-2xl border border-blue-100 bg-blue-50 p-4 text-sm leading-6 text-blue-950">
              <div className="font-black">{message || 'Enter the code from your email.'}</div>
              <div className="mt-1 text-xs">Sent to {email}</div>
            </div>
            <label className="mt-5 block text-xs font-black uppercase tracking-[0.12em] text-slate-500">Verification code</label>
            <input required inputMode="numeric" autoComplete="one-time-code" value={otp} onChange={(event) => setOtp(event.target.value)} placeholder="Enter code" className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-center text-lg font-black tracking-[0.2em] text-slate-950 outline-none" />
            {error && <div className="mt-4 rounded-xl bg-rose-50 p-3 text-xs font-bold text-rose-700">{error}</div>}
            <button disabled={busy || !otp.trim()} className="mt-5 w-full rounded-2xl bg-slate-950 px-4 py-3 text-sm font-black text-white disabled:opacity-40">{busy ? 'Verifying…' : 'Verify & continue'}</button>
            <button type="button" onClick={() => { setStep('email'); setOtp(''); setError('') }} className="mt-3 w-full px-4 py-2 text-xs font-black text-blue-700">Use a different email</button>
          </form>
        )}
      </div>
    </div>
  )
}

export function AccountButton({ compact = false }) {
  const { loading, user, configured } = useAuth()
  const [open, setOpen] = useState(false)

  const label = loading
    ? 'Account'
    : user
      ? (user.profile?.name || user.email || 'Account')
      : 'Sign in'

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={user ? 'Open account' : 'Sign in to Sports Zenith'}
        className={compact
          ? 'flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700'
          : 'inline-flex items-center gap-2 rounded-2xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-black text-slate-700 shadow-sm transition hover:border-blue-200 hover:text-blue-700'}
      >
        <UserRound size={16} />
        {!compact && <span className="max-w-32 truncate">{configured ? label : 'Account'}</span>}
      </button>
      {open && <AccountModal onClose={() => setOpen(false)} />}
    </>
  )
}
