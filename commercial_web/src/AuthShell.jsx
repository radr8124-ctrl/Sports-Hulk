import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import { ArrowLeft, ArrowRight, CheckCircle2, LogOut, Mail, ShieldCheck, UserRound, X } from 'lucide-react'
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

  const maskedEmail = useMemo(() => {
    const [name = '', domain = ''] = email.split('@')
    if (!domain) return email
    return `${name.slice(0, 2)}${name.length > 2 ? '•••' : ''}@${domain}`
  }, [email])

  const requestCode = async (event) => {
    event?.preventDefault?.()
    if (!email.trim()) return
    setBusy(true)
    setError('')
    setMessage('')
    try {
      const result = await sendOtp(email.trim())
      if (result.error) throw result.error
      setStep('code')
      setMessage('We sent a secure 6-digit code to your email.')
    } catch (err) {
      setError(err?.message || 'Could not send a sign-in code. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  const verifyCode = async (event) => {
    event.preventDefault()
    if (otp.trim().length !== 6) return
    setBusy(true)
    setError('')
    try {
      const result = await verifyOtp(email.trim(), otp.trim())
      if (result.error) throw result.error
      onClose()
    } catch (err) {
      setError(err?.message || 'That code could not be verified. Check the code and try again.')
    } finally {
      setBusy(false)
    }
  }

  const resendCode = async () => {
    setOtp('')
    await requestCode()
  }

  const doSignOut = async () => {
    setBusy(true)
    await signOut()
    setBusy(false)
    onClose()
  }

  return (
    <div className="fixed inset-0 z-[80] flex items-end justify-center bg-slate-950/50 p-0 backdrop-blur-[5px] sm:items-center sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="sports-zenith-auth-title"
        onClick={(event) => event.stopPropagation()}
        className="w-full overflow-hidden rounded-t-[32px] border-t border-white/80 bg-white shadow-2xl sm:max-w-[470px] sm:rounded-[32px] sm:border"
      >
        <div className="h-1.5 bg-blue-700" />
        <div className="mx-auto mt-3 h-1 w-11 rounded-full bg-slate-200 sm:hidden" />
        <div className="px-5 pb-7 pt-4 sm:p-7">
          {!configured ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-700 sm:text-[11px]">Sports Zenith</div>
                  <div id="sports-zenith-auth-title" className="mt-2 text-[28px] font-black tracking-[-0.04em] text-slate-950">Account unavailable</div>
                </div>
                <button type="button" aria-label="Close account dialog" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-500"><X size={18} /></button>
              </div>
              <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm font-semibold leading-6 text-amber-950">Account services are not configured in this build.</div>
            </>
          ) : user ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-700 sm:text-[11px]">Sports Zenith</div>
                  <div id="sports-zenith-auth-title" className="mt-2 text-[28px] font-black tracking-[-0.04em] text-slate-950">Your account</div>
                </div>
                <button type="button" aria-label="Close account dialog" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 text-slate-500"><X size={18} /></button>
              </div>
              <div className="mt-6 rounded-3xl border border-slate-200 bg-slate-50 p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-slate-950 text-lg font-black text-white">{(user.profile?.name || user.email || 'S').slice(0, 1).toUpperCase()}</div>
                  <div className="min-w-0">
                    <div className="truncate font-black text-slate-950">{user.profile?.name || 'Sports Zenith member'}</div>
                    <div className="truncate text-sm font-semibold text-slate-500">{user.email}</div>
                  </div>
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs font-bold text-emerald-700"><CheckCircle2 size={15} /> {user.emailVerified ? 'Email verified' : 'Signed in'}</div>
              </div>
              <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50 p-4 text-xs leading-5 text-blue-900">This verified account is the identity for your private Survivor data, future fantasy connections, saved preferences and subscription access.</div>
              <button type="button" disabled={busy} onClick={doSignOut} className="mt-5 flex h-12 w-full items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 text-sm font-black text-slate-700 disabled:opacity-50"><LogOut size={16} /> Sign out</button>
            </>
          ) : step === 'email' ? (
            <form onSubmit={requestCode}>
              <div className="flex items-start justify-between gap-5">
                <div>
                  <div className="text-[10px] font-black uppercase tracking-[0.2em] text-blue-700 sm:text-[11px]">Sports Zenith</div>
                  <h2 id="sports-zenith-auth-title" className="mt-2 text-[28px] font-black tracking-[-0.04em] text-slate-950 sm:text-[30px]">Sign in to continue</h2>
                  <p className="mt-2 max-w-sm text-sm font-medium leading-6 text-slate-500">Access saved picks, private Survivor entries, fantasy connections and future member features.</p>
                </div>
                <button type="button" aria-label="Close sign in" onClick={onClose} className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-500"><X size={18} /></button>
              </div>

              <label htmlFor="sports-zenith-email" className="mt-7 block text-xs font-black uppercase tracking-[0.12em] text-slate-600">Email address</label>
              <div className="mt-2 flex h-14 items-center gap-3 rounded-2xl border border-slate-300 bg-white px-4 shadow-sm transition focus-within:border-blue-500 focus-within:ring-4 focus-within:ring-blue-50">
                <Mail size={19} className="text-slate-400" />
                <input id="sports-zenith-email" required autoFocus type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="you@example.com" className="min-w-0 flex-1 bg-transparent text-base font-semibold text-slate-950 outline-none placeholder:text-slate-400" />
              </div>

              {authConfig?.requireEmailVerification && <div className="mt-3 text-[11px] font-semibold leading-5 text-slate-400">Your email is verified as part of this secure sign-in.</div>}
              {error && <div className="mt-3 rounded-xl bg-rose-50 px-3 py-2.5 text-xs font-bold text-rose-700">{error}</div>}

              <button disabled={busy || !email.trim()} className="mt-4 flex h-14 w-full items-center justify-center gap-2 rounded-2xl bg-slate-950 px-5 text-[15px] font-black text-white shadow-lg shadow-slate-950/10 transition hover:-translate-y-0.5 disabled:cursor-not-allowed disabled:opacity-45">{busy ? 'Sending…' : 'Continue'} {!busy && <ArrowRight size={18} />}</button>

              <div className="mt-5 flex items-start gap-3 rounded-2xl border border-blue-100 bg-blue-50/80 px-4 py-3.5">
                <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-white text-blue-700 shadow-sm"><ShieldCheck size={16} /></div>
                <div>
                  <div className="text-xs font-black text-slate-900">No password to remember</div>
                  <div className="mt-0.5 text-xs font-medium leading-5 text-slate-500">We’ll email a secure 6-digit code. New members use this same flow — no separate signup form.</div>
                </div>
              </div>

              <div className="mt-5 border-t border-slate-100 pt-4 text-center text-[11px] font-semibold leading-5 text-slate-400">Your verified email becomes the identity for private data, saved preferences and future subscription access.</div>
            </form>
          ) : (
            <form onSubmit={verifyCode}>
              <button type="button" onClick={() => { setStep('email'); setOtp(''); setError(''); setMessage('') }} className="inline-flex items-center gap-1.5 text-xs font-black text-blue-700"><ArrowLeft size={15} /> Back</button>
              <div className="mt-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-blue-50 text-blue-700"><Mail size={23} /></div>
              <div className="mt-5 text-[10px] font-black uppercase tracking-[0.2em] text-blue-700 sm:text-[11px]">Secure verification</div>
              <h2 id="sports-zenith-auth-title" className="mt-2 text-[28px] font-black tracking-[-0.04em] text-slate-950 sm:text-[30px]">Check your email</h2>
              <p className="mt-2 text-sm font-medium leading-6 text-slate-500">Enter the 6-digit code sent to <span className="font-black text-slate-700">{maskedEmail}</span>.</p>

              <label htmlFor="sports-zenith-otp" className="mt-7 block text-xs font-black uppercase tracking-[0.12em] text-slate-600">Verification code</label>
              <input id="sports-zenith-otp" required autoFocus inputMode="numeric" autoComplete="one-time-code" maxLength={6} value={otp} onChange={(event) => setOtp(event.target.value.replace(/\D/g, '').slice(0, 6))} placeholder="000000" className="mt-2 h-16 w-full rounded-2xl border border-slate-300 bg-white px-4 text-center text-2xl font-black tracking-[0.38em] text-slate-950 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-50" />

              {message && <div className="mt-3 text-center text-[11px] font-semibold text-slate-400">{message}</div>}
              {error && <div className="mt-3 rounded-xl bg-rose-50 px-3 py-2.5 text-xs font-bold text-rose-700">{error}</div>}

              <button disabled={busy || otp.length !== 6} className="mt-4 flex h-14 w-full items-center justify-center rounded-2xl bg-slate-950 px-5 text-[15px] font-black text-white shadow-lg shadow-slate-950/10 disabled:cursor-not-allowed disabled:opacity-45">{busy ? 'Verifying…' : 'Verify & continue'}</button>
              <button type="button" disabled={busy} onClick={resendCode} className="mt-4 w-full text-center text-xs font-black text-blue-700 disabled:opacity-40">Send a new code</button>

              <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-center text-[11px] font-semibold leading-5 text-slate-500">For security, verification codes are short-lived and can only be used once.</div>
            </form>
          )}
        </div>
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
