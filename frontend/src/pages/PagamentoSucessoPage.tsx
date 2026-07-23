/**
 * AYRIA - Página de Sucesso do Pagamento Stripe
 * 🆕 22/07 22:08 — Após pagar no Stripe, user cai aqui
 * Mostra loading enquanto webhook chega, depois redireciona pro /chat
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { CheckCircle2, Loader2 } from 'lucide-react'
import { useAuth } from '../store/auth'

export function PagamentoSucessoPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const sessionId = params.get('session_id') || params.get('sessionId')
  const { user, loadUser } = useAuth()
  const [phase, setPhase] = useState<'loading' | 'ready' | 'timeout'>('loading')
  const [secondsLeft, setSecondsLeft] = useState(15)

  // Refresh user + verifica se subscription já chegou (webhook pode demorar 3-10s)
  useEffect(() => {
    let cancelled = false
    const tick = async () => {
      if (cancelled) return
      await loadUser()
    }
    tick()
    const interval = setInterval(tick, 2000)
    const timeout = setTimeout(() => {
      if (!cancelled) {
        clearInterval(interval)
        setPhase('timeout')
      }
    }, 30000)
    return () => {
      cancelled = true
      clearInterval(interval)
      clearTimeout(timeout)
    }
  }, [loadUser])

  // Quando user passa a ter subscription ativa, manda pro /chat
  useEffect(() => {
    if (!user) return
    const hasActiveSubscription = !!user.external_subscription_id && user.billing_status === 'active'
    if (hasActiveSubscription) {
      setPhase('ready')
      const t = setTimeout(() => navigate('/chat', { replace: true }), 1500)
      return () => clearTimeout(t)
    }
  }, [user, navigate])

  // Countdown visível
  useEffect(() => {
    if (phase !== 'loading') return
    const i = setInterval(() => setSecondsLeft((s) => Math.max(0, s - 1)), 1000)
    return () => clearInterval(i)
  }, [phase])

  const goChat = () => navigate('/chat', { replace: true })
  const goPlanos = () => navigate('/planos', { replace: true })

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'linear-gradient(135deg, #0B1020 0%, #121A2F 45%, #1D2A47 100%)' }}
    >
      <div
        className="w-full max-w-md rounded-2xl p-8 text-center"
        style={{ background: 'rgba(18, 26, 47, 0.85)', border: '1px solid #2a2a3e', backdropFilter: 'blur(12px)' }}
      >
        {phase === 'ready' && (
          <>
            <CheckCircle2 size={64} className="mx-auto mb-4" style={{ color: '#10B981' }} />
            <h1 className="text-2xl font-bold text-white mb-2">Pagamento confirmado! ✅</h1>
            <p className="text-sm text-gray-400 mb-4">
              Plano <span className="font-bold text-ayria-gold">{user?.billing_status || 'ativado'}</span> ativo.
              Redirecionando pro chat...
            </p>
            <Loader2 className="animate-spin mx-auto" size={20} style={{ color: '#D4AF37' }} />
          </>
        )}

        {phase === 'loading' && (
          <>
            <Loader2 size={64} className="animate-spin mx-auto mb-4" style={{ color: '#D4AF37' }} />
            <h1 className="text-2xl font-bold text-white mb-2">Processando pagamento...</h1>
            <p className="text-sm text-gray-400 mb-1">
              Estamos confirmando sua assinatura com o Stripe.
            </p>
            <p className="text-xs text-gray-500 mb-4">
              Isso leva entre 5-15 segundos.
            </p>
            <div className="text-xs text-gray-600">
              {sessionId && <>Sessão Stripe: <span className="font-mono">{sessionId.slice(0, 20)}...</span></>}
            </div>
            <div className="mt-6">
              <button
                onClick={goChat}
                className="text-xs underline"
                style={{ color: '#818CF8' }}
              >
                Já esperei demais? Tentar entrar no chat →
              </button>
            </div>
          </>
        )}

        {phase === 'timeout' && (
          <>
            <div className="text-5xl mb-4">⏳</div>
            <h1 className="text-2xl font-bold text-white mb-2">Demorou mais que o esperado</h1>
            <p className="text-sm text-gray-400 mb-4">
              Seu pagamento foi enviado pro Stripe, mas ainda não confirmamos a ativação.
              Pode tentar entrar no chat — se ainda não aparecer, aguarde mais alguns segundos
              e atualize.
            </p>
            <div className="flex gap-2 justify-center mt-4">
              <button
                onClick={goChat}
                className="px-4 py-2 rounded-xl text-white font-medium"
                style={{ background: 'linear-gradient(135deg, #D4AF37 0%, #E8C768 100%)', color: '#0B1020' }}
              >
                Ir pro Chat
              </button>
              <button
                onClick={goPlanos}
                className="px-4 py-2 rounded-xl text-gray-300"
                style={{ border: '1px solid #2a2a3e' }}
              >
                Ver Planos
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export default PagamentoSucessoPage