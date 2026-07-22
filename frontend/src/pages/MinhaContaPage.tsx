/**
 * AYRIA - Minha Conta Page (19/07/2026)
 *
 * Mostra assinatura ativa + créditos + botão "Gerenciar assinatura" (Customer Portal).
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { stripeApi } from '../lib/api'
import { LogoIcon } from '../components/Logo'

export function MinhaContaPage() {
  const [loading, setLoading] = useState(true)
  const [data, setData] = useState<any>(null)
  const [openingPortal, setOpeningPortal] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const load = async () => {
    try {
      const r = await stripeApi.getMySubscription()
      setData(r.data)
      setLoading(false)
    } catch (e: any) {
      setError(e.message)
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleManageSubscription = async () => {
    setOpeningPortal(true)
    try {
      const r = await stripeApi.createPortalSession()
      window.location.href = r.data.url
    } catch (e: any) {
      setError(e?.response?.data?.detail || e.message)
      setOpeningPortal(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--ayria-bg)' }}>
        <div className="text-white text-lg">Carregando...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--ayria-bg)' }}>
        <div className="text-red-400 text-center">
          <div className="text-xl mb-4">⚠️</div>
          <div>{error}</div>
        </div>
      </div>
    )
  }

  const sub = data?.active_subscription

  return (
    <div className="min-h-screen px-4 py-12" style={{ background: 'var(--ayria-bg)' }}>
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <LogoIcon size={40} />
          <h1 className="text-2xl font-bold text-white">Minha Conta</h1>
        </div>

        {/* Card saldo */}
        <div className="rounded-2xl p-6 mb-4"
          style={{ background: 'linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(99, 102, 241, 0.15))', border: '1px solid rgba(212, 175, 55, 0.3)' }}>
          <div className="text-purple-400 text-sm mb-1">Saldo atual</div>
          <div className="text-4xl font-bold text-white mb-2">
            {data?.credit_balance?.toLocaleString('pt-BR') || 0} <span className="text-xl font-normal text-ayria-muted">tokens</span>
          </div>
          {sub && (
            <div className="text-ayria-muted text-sm">
              Renova todo mês conforme seu plano
            </div>
          )}
        </div>

        {/* Card assinatura */}
        {sub ? (
          <div className="rounded-2xl p-6 mb-4"
            style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <div className="flex items-center justify-between mb-4">
              <div>
                <div className="text-white font-bold text-lg">Plano {sub.plan_name}</div>
                <div className="text-ayria-muted text-sm capitalize">
                  Status: <span className={
                    sub.status === 'active' ? 'text-green-400' :
                    sub.status === 'past_due' ? 'text-yellow-400' :
                    sub.status === 'canceled' ? 'text-red-400' :
                    'text-ayria-muted'
                  }>{sub.status}</span>
                </div>
              </div>
              <button
                onClick={handleManageSubscription}
                disabled={openingPortal}
                className="px-4 py-2 rounded-lg font-semibold text-white disabled:opacity-50"
                style={{ background: 'linear-gradient(90deg, #A855F7, #6366F1)' }}
              >
                {openingPortal ? 'Abrindo...' : 'Gerenciar assinatura'}
              </button>
            </div>
            {sub.current_period_end && (
              <div className="text-ayria-muted text-xs">
                {sub.cancel_at_period_end
                  ? `Cancela em: ${new Date(sub.current_period_end).toLocaleDateString('pt-BR')}`
                  : `Próxima cobrança: ${new Date(sub.current_period_end).toLocaleDateString('pt-BR')}`
                }
              </div>
            )}
          </div>
        ) : (
          <div className="rounded-2xl p-6 mb-4 text-center"
            style={{ background: 'rgba(255, 255, 255, 0.03)', border: '1px solid rgba(255, 255, 255, 0.1)' }}>
            <div className="text-ayria-muted mb-4">
              Você ainda não tem uma assinatura ativa.
            </div>
            <button
              onClick={() => navigate('/planos')}
              className="px-6 py-3 rounded-lg font-semibold text-white"
              style={{ background: 'linear-gradient(90deg, #A855F7, #6366F1)' }}
            >
              Ver planos
            </button>
          </div>
        )}

        <div className="text-center mt-8">
          <button
            onClick={() => navigate('/chat')}
            className="text-ayria-muted hover:text-white text-sm underline"
          >
            ← Voltar pro chat
          </button>
        </div>
      </div>
    </div>
  )
}