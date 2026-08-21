/**
 * AYRIA - Paywall Modal (20/08/2026)
 *
 * Aparece quando o user tenta mandar mensagem sem creditos (402).
 * Mostra CTAs comerciais pra escolher um plano pago.
 *
 * Features:
 * - Bloqueia interação com o chat até user escolher ação
 * - Lista planos pagos (basico/intermediario/premium) com preço
 * - Botão "Escolher um plano" → /planos
 * - Botão "Voltar depois" → fecha modal
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { stripeApi, StripePlan } from '../lib/api'

interface PaywallModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  const navigate = useNavigate()
  const [plans, setPlans] = useState<StripePlan[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isOpen && plans.length === 0) {
      setLoading(true)
      stripeApi.getConfig()
        .then(r => {
          // Só planos pagos (sem trial)
          setPlans(r.data.plans.filter(p => p.slug !== 'trial'))
        })
        .catch(() => {})
        .finally(() => setLoading(false))
    }
  }, [isOpen])

  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl p-8 relative"
        style={{
          background: 'linear-gradient(135deg, #1a0a2e, #0a0518)',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          boxShadow: '0 0 60px rgba(168, 85, 247, 0.2)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-ayria-muted hover:text-white text-2xl leading-none"
          aria-label="Fechar"
        >
          ×
        </button>

        {/* Header */}
        <div className="text-center mb-6">
          <div className="text-5xl mb-3">🔒</div>
          <h2 className="text-3xl font-bold text-white mb-2">
            Seus créditos acabaram
          </h2>
          <p className="text-ayria-muted text-lg">
            Continue sua jornada de autoconhecimento escolhendo um plano.
          </p>
        </div>

        {/* Planos rápidos */}
        {!loading && plans.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            {plans.map((plan) => (
              <button
                key={plan.slug}
                onClick={() => navigate('/planos')}
                className="rounded-lg p-4 text-left transition hover:scale-105"
                style={{
                  background: plan.slug === 'premium'
                    ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.2), rgba(99, 102, 241, 0.2))'
                    : 'rgba(255,255,255,0.05)',
                  border: plan.slug === 'premium'
                    ? '2px solid rgba(168, 85, 247, 0.5)'
                    : '1px solid rgba(255,255,255,0.1)'
                }}
              >
                <div className="text-sm font-bold text-white mb-1">{plan.name}</div>
                <div className="text-2xl font-bold text-white">
                  R$ {plan.price_brl.toFixed(2).replace('.', ',')}
                </div>
                <div className="text-xs text-ayria-muted">
                  {plan.tokens.toLocaleString('pt-BR')} tokens / mês
                </div>
              </button>
            ))}
          </div>
        )}

        {/* CTAs */}
        <div className="flex flex-col gap-3">
          <button
            onClick={() => navigate('/planos')}
            className="w-full py-3 rounded-lg font-semibold text-white text-base transition hover:opacity-90"
            style={{ background: 'linear-gradient(90deg, #da950b, #f1c961)' }}
          >
            Ver todos os planos
          </button>
          <button
            onClick={onClose}
            className="w-full py-2 text-ayria-muted hover:text-white text-sm"
          >
            Voltar depois
          </button>
        </div>

        <p className="text-center text-xs text-ayria-muted mt-4">
          💳 Pagamento seguro processado pela Stripe. Cancele quando quiser.
        </p>
      </div>
    </div>
  )
}
