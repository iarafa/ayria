/**
 * AYRIA - Verify Email Page
 * Processa o link de verificação enviado por email.
 * /verify-email?token=...
 *
 * Comportamento:
 *  - Carrega, mostra spinner
 *  - Chama /api/auth/verify-email?token=...
 *  - Sucesso: redireciona automático pro /login em 2s (08/07/2026 — era clique manual)
 *  - Email já verificado: redireciona automático pro /login em 2s
 *  - Erro (expirado/inválido): mostra erro + botão "Criar nova conta" + link secundário "Voltar pro login"
 */
import { useEffect, useState } from 'react'
import { useSearchParams, Link, useNavigate } from 'react-router-dom'
import { LogoIcon } from '../components/Logo'
import { api } from '../lib/api'

type Status = 'loading' | 'success' | 'expired' | 'invalid' | 'already'

export function VerifyEmailPage() {
  const [params] = useSearchParams()
  const token = params.get('token')
  const navigate = useNavigate()
  const [status, setStatus] = useState<Status>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  // 🆕 UX fix 15/07/2026: remove auto-redirect 2s — user pediu botão "OK" manual.
  // (Antes redirecionava sozinho; agora fica na tela até o user clicar.)
  // useEffect(() => { if (status === 'success' || status === 'already') { ... } }, [status, navigate])

  useEffect(() => {
    if (!token) {
      setStatus('invalid')
      setErrorMsg('Token não fornecido.')
      return
    }

    api.get(`/api/auth/verify-email?token=${encodeURIComponent(token)}`)
      .then(({ data }) => {
        if (data?.already_verified) {
          setStatus('already')
        } else {
          setStatus('success')
        }
      })
      .catch((e: any) => {
        const detail = e?.response?.data?.detail || 'Erro ao verificar email.'
        const code = e?.response?.status
        if (code === 410) {
          setStatus('expired')
        } else if (code === 404) {
          setStatus('invalid')
        } else {
          setStatus('invalid')
        }
        setErrorMsg(detail)
      })
  }, [token])

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: 'radial-gradient(ellipse at center, #1a0a2e 0%, #050505 70%)' }}
    >
      <div className="w-full max-w-md text-center space-y-6">
        <div className="flex justify-center">
          <LogoIcon size={80} variant="circular" />
        </div>

        {status === 'loading' && (
          <>
            <div className="flex justify-center">
              <div className="w-16 h-16 rounded-full border-4 border-t-transparent animate-spin"
                style={{ borderColor: 'rgba(99, 102, 241, 0.3)', borderTopColor: '#6366F1' }} />
            </div>
            <p className="text-ayria-muted">Confirmando seu email...</p>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(16, 185, 129, 0.15)' }}>
                <span className="text-5xl">✅</span>
              </div>
            </div>
            <h1 className="text-3xl font-bold gradient-text">Email confirmado!</h1>
            <p className="text-ayria-muted">
              Sua conta foi ativada com sucesso.
            </p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
            >
              OK, ir pro login
            </button>
          </>
        )}

        {status === 'already' && (
          <>
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
                <span className="text-5xl">ℹ️</span>
              </div>
            </div>
            <h1 className="text-2xl font-bold text-ayria-text">Email já verificado</h1>
            <p className="text-ayria-muted">
              Sua conta já está ativa. Pode fazer login.
            </p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
            >
              OK, ir pro login
            </button>
          </>
        )}

        {(status === 'expired' || status === 'invalid') && (
          <>
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full flex items-center justify-center"
                style={{ background: 'rgba(239, 68, 68, 0.15)' }}>
                <span className="text-5xl">⚠️</span>
              </div>
            </div>
            <h1 className="text-2xl font-bold text-ayria-text">
              {status === 'expired' ? 'Link expirado' : 'Link inválido'}
            </h1>
            <p className="text-ayria-muted">{errorMsg}</p>
            <Link
              to="/register"
              className="inline-block px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90"
              style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
            >
              Criar nova conta
            </Link>
            <p className="text-sm text-ayria-muted">
              Já tem conta?{' '}
              <Link
                to="/login"
                className="underline opacity-80 hover:opacity-100 transition-opacity"
              >
                Voltar pro login
              </Link>
            </p>
          </>
        )}
      </div>
    </div>
  )
}
