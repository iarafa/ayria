/**
 * AYRIA - Register Page (com seleção de plano)
 */
import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { LogoIcon } from '../components/Logo'
import { api } from '../lib/api'
import { Check, Sparkles } from 'lucide-react'

interface Plan {
  id: string
  name: string
  slug: string
  credits: number
  price_brl: number
  active: boolean
}

export function RegisterPage() {
  const { register, loading, error } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [plans, setPlans] = useState<Plan[]>([])
  const [selectedPlanSlug, setSelectedPlanSlug] = useState<string | null>(null)
  const [plansLoading, setPlansLoading] = useState(true)
  const [verificationSent, setVerificationSent] = useState(false)
  const [resendCooldown, setResendCooldown] = useState(0)
  const navigate = useNavigate()

  // Carrega planos do backend
  useEffect(() => {
    api.get('/api/plans')
      .then(({ data }) => setPlans(data as Plan[]))
      .catch(() => setPlans([]))
      .finally(() => setPlansLoading(false))
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedPlanSlug) return
    const ok = await register(email, password, fullName || undefined, selectedPlanSlug)
    if (ok) {
      // 🆕 Após register (07/07/2026): se não tem token salvo, é pq email verification está ativo
      const tokenAfter = localStorage.getItem('ayria_token')
      if (!tokenAfter) {
        // Mostra tela "verifique seu email"
        setVerificationSent(true)
      } else {
        navigate('/onboarding')
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
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
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
          <LogoIcon size={80} variant="circular" />
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

          {/* SELEÇÃO DE PLANO */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <Sparkles size={16} className="text-ayria-primary" />
              <h2 className="text-lg font-semibold text-ayria-text">Escolha seu plano</h2>
            </div>
            <p className="text-xs text-ayria-muted mb-4">
              O plano já libera seu saldo inicial para uso. <strong>Cobrança ainda não está ativa.</strong> Créditos são usados pra conversar com a AYRIA. Onboarding e leituras de perfil não descontam.
            </p>

            {plansLoading ? (
              <div className="text-center text-ayria-muted py-4">Carregando planos...</div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {plans.map((plan) => {
                  const selected = selectedPlanSlug === plan.slug
                  return (
                    <button
                      key={plan.id}
                      type="button"
                      onClick={() => setSelectedPlanSlug(plan.slug)}
                      className="relative text-left p-4 rounded-2xl transition-all hover:scale-[1.02]"
                      style={{
                        background: selected
                          ? 'linear-gradient(135deg, rgba(99,102,241,0.15), rgba(168,85,247,0.15))'
                          : '#111111',
                        border: selected
                          ? '2px solid #A855F7'
                          : '1px solid #1E1E2E',
                        boxShadow: selected
                          ? '0 0 24px rgba(168, 85, 247, 0.3)'
                          : 'none',
                      }}
                    >
                      {selected && (
                        <div
                          className="absolute -top-2 -right-2 w-7 h-7 rounded-full flex items-center justify-center"
                          style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
                        >
                          <Check size={14} className="text-white" />
                        </div>
                      )}
                      <div className="font-bold text-ayria-text mb-1">{plan.name}</div>
                      <div className="text-2xl font-bold gradient-text mb-1">
                        {plan.credits.toLocaleString('pt-BR')}
                      </div>
                      <div className="text-xs text-ayria-muted mb-3">créditos iniciais</div>
                      <div className="text-sm text-ayria-text">
                        <span className="text-ayria-muted text-xs">R$ </span>
                        <span className="font-semibold">
                          {plan.price_brl.toFixed(2).replace('.', ',')}
                        </span>
                        <span className="text-ayria-muted text-xs"> /mês ref.</span>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
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
            disabled={loading || !selectedPlanSlug}
            className="w-full py-3 rounded-xl font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            {loading ? 'Criando...' : selectedPlanSlug ? 'Criar conta e começar' : 'Escolha um plano'}
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
