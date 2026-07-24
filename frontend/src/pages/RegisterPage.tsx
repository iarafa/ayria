/**
 * AYRIA - Register Page (sem seleção de plano — plano escolhido no checkup/onboarding)
 */
import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { LogoIcon } from '../components/Logo'
import { api } from '../lib/api'

export function RegisterPage() {
  const { register, loading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [verificationSent, setVerificationSent] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const ok = await register(email, password, fullName || undefined)
    if (ok) {
      // 🆕 23/07/2026: usa verification_sent do backend (não chutar baseado em token)
      const { verification_sent } = useAuth.getState()
      if (verification_sent === false) {
        // Email FALHOU — backend mandou email_error mas criou a conta
        setVerificationSent(false)
      } else {
        // Caminho padrão: sem token + verificação OK
        const tokenAfter = localStorage.getItem('ayria_token')
        if (!tokenAfter) {
          setVerificationSent(true)
        } else {
          navigate('/onboarding')
        }
      }
    }
  }

  // 🆕 Cooldown do reenvio (countdown)
  useEffect(() => {
    if (resendCooldown <= 0) return
    const t = setTimeout(() => setResendCooldown(c => c - 1), 1000)
    return () => clearTimeout(t)
  }, [resendCooldown])

  const handleResend = async () => {
    if (resendCooldown > 0) return
    try {
      await api.post('/api/auth/resend-verification', { email })
      setResendCooldown(60)
    } catch (e: any) {
      const detail = e?.response?.data?.detail || 'Erro ao reenviar'
      if (detail.includes('60 segundos')) {
        setResendCooldown(60)
      } else {
        alert(detail)
      }
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 py-12"
      style={{ background: 'radial-gradient(ellipse at center, #1a0a2e 0%, #050505 70%)' }}
    >
      <div className="w-full max-w-3xl">
        {/* Logo + título */}

        {/* 🆕 Tela "Verifique seu email" (07/07/2026) */}
        {verificationSent ? (
          <div className="space-y-6 text-center">
            <div className="flex justify-center">
              <div className="w-20 h-20 rounded-full flex items-center justify-center" style={{ background: 'rgba(99, 102, 241, 0.15)' }}>
                <span className="text-5xl">📬</span>
              </div>
            </div>
            <h1 className="text-3xl font-bold gradient-text">Confirme seu email</h1>
            <p className="text-ayria-muted max-w-md mx-auto leading-relaxed">
              Enviamos um link de confirmação para <strong className="text-ayria-text">{email}</strong>.
              Clique no link pra ativar sua conta e começar a usar a AYRIA.
            </p>
            <div className="px-6 py-4 rounded-xl text-sm" style={{ background: 'rgba(99, 102, 241, 0.08)', border: '1px solid rgba(99, 102, 241, 0.2)', color: '#A5B4FC' }}>
              ⏰ O link expira em 24 horas. Verifique também a caixa de spam.
            </div>
            <div className="flex flex-col sm:flex-row gap-3 justify-center pt-4">
              <button
                type="button"
                onClick={handleResend}
                disabled={resendCooldown > 0}
                className="px-6 py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
              >
                {resendCooldown > 0 ? `Reenviar em ${resendCooldown}s` : 'Reenviar email'}
              </button>
              <Link
                to="/login"
                className="px-6 py-3 rounded-xl font-semibold text-center transition-opacity hover:opacity-90"
                style={{ background: '#1E1E2E', color: '#fff' }}
              >
                Ir pro login
              </Link>
            </div>
          </div>
        ) : (
        <>
        <div className="flex justify-center mb-6">
          <LogoIcon size={400} variant="circular" className="max-w-[85vw]" />
        </div>

        <h1 className="text-3xl font-bold text-center mb-2 gradient-text">
          Crie sua conta
        </h1>
        <p className="text-center text-ayria-muted mb-8">
          Comece sua jornada de autoconhecimento com AYRIA
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* DADOS PESSOAIS */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-ayria-muted mb-2">Nome</label>
              <input
                type="text"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                style={{ background: '#111111', border: '1px solid #1E1E2E' }}
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm text-ayria-muted mb-2">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>

              <div>
                <label className="block text-sm text-ayria-muted mb-2">Senha (mín 8 chars)</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={8}
                  className="w-full px-4 py-3 rounded-xl text-ayria-text outline-none"
                  style={{ background: '#111111', border: '1px solid #1E1E2E' }}
                />
              </div>
            </div>
          </div>

          {error && (
            <div
              className="px-4 py-2 rounded-lg text-sm"
              style={{ background: 'rgba(239, 68, 68, 0.1)', color: '#EF4444' }}
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
          >
            {loading ? 'Criando...' : 'Criar conta e começar'}
          </button>
        </form>

        <p className="text-center text-ayria-muted mt-6">
          Já tem conta?{' '}
          <Link to="/login" className="text-ayria-primary hover:underline">
            Entrar
          </Link>
        </p>
        </>
        )}
      </div>
    </div>
  )
}
