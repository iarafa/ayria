/**
 * AYRIA - Pagamento Sucesso Page (19/07/2026)
 *
 * Redirect do Stripe Checkout. Verifica status da assinatura.
 *
 * Cenários:
 * - Pagamento OK + webhook já processou → mostra "Bem-vindo!" + créditos
 * - Pagamento OK + webhook ainda não chegou → mostra "Processando..." + polling
 * - session_id inválido → mostra erro
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { stripeApi } from '../lib/api'
import { LogoIcon } from '../components/Logo'

export function PagamentoSucessoPage() {
  const [searchParams] = useSearchParams()
  const sessionId = searchParams.get('session_id')
  const [status, setStatus] = useState<'loading' | 'active' | 'pending' | 'error'>('loading')
  const [message, setMessage] = useState<string>('')
  const [credits, setCredits] = useState<number | null>(null)
  const [planName, setPlanName] = useState<string>('')
  const navigate = useNavigate()

  useEffect(() => {
    if (!sessionId) {
      setStatus('error')
      setMessage('Sessão não encontrada. Verifique se o pagamento foi processado.')
      return
    }

    let attempts = 0
    const maxAttempts = 8  // ~16s

    const checkStatus = async () => {
      try {
        const r = await stripeApi.getMySubscription()
        const data = r.data
        setCredits(data.credit_balance)
        if (data.active_subscription) {
          setStatus('active')
          setPlanName(data.active_subscription.plan_name || '')
          return true  // para polling
        }
        return false
      } catch (e: any) {
        setStatus('error')
        setMessage(`Erro: ${e.message}`)
        return true
      }
    }

    const interval = setInterval(async () => {
      attempts++
      const done = await checkStatus()
      if (done || attempts >= maxAttempts) {
        clearInterval(interval)
        if (attempts >= maxAttempts && status === 'loading') {
          setStatus('pending')
          setMessage('Seu pagamento está sendo processado. Em alguns segundos sua assinatura será ativada.')
        }
      }
    }, 2000)

    checkStatus()  // primeira tentativa imediata

    return () => clearInterval(interval)
  }, [sessionId])

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--ayria-bg)' }}>
      <div className="max-w-md w-full text-center">
        <div className="flex items-center justify-center mb-8">
          <LogoIcon size={64} variant="circular" />
        </div>

        {status === 'loading' && (
          <>
            <div className="text-6xl mb-6">⏳</div>
            <h2 className="text-2xl font-bold text-white mb-4">Confirmando seu pagamento...</h2>
            <p className="text-ayria-muted">Aguarde alguns segundos.</p>
          </>
        )}

        {status === 'active' && (
          <>
            <div className="text-6xl mb-6">🎉</div>
            <h2 className="text-2xl font-bold text-white mb-4">Bem-vindo ao plano {planName}!</h2>
            <p className="text-ayria-muted mb-2">
              Sua assinatura está ativa.
            </p>
            {credits !== null && (
              <div className="my-6 p-4 rounded-xl"
                style={{ background: 'rgba(212, 175, 55, 0.1)', border: '1px solid rgba(212, 175, 55, 0.3)' }}>
                <div className="text-purple-400 text-sm mb-1">Seu saldo</div>
                <div className="text-3xl font-bold text-white">{credits.toLocaleString('pt-BR')} tokens</div>
              </div>
            )}
            <button
              onClick={() => navigate('/chat')}
              className="w-full py-3 rounded-lg font-semibold text-white"
              style={{ background: 'linear-gradient(90deg, #A855F7, #6366F1)' }}
            >
              Conversar com AYRIA
            </button>
          </>
        )}

        {status === 'pending' && (
          <>
            <div className="text-6xl mb-6">⏱️</div>
            <h2 className="text-2xl font-bold text-white mb-4">Quase lá!</h2>
            <p className="text-ayria-muted mb-6">{message}</p>
            <button
              onClick={() => window.location.reload()}
              className="w-full py-3 rounded-lg font-semibold text-white"
              style={{ background: 'rgba(255, 255, 255, 0.08)' }}
            >
              Atualizar página
            </button>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="text-6xl mb-6">⚠️</div>
            <h2 className="text-2xl font-bold text-white mb-4">Algo deu errado</h2>
            <p className="text-ayria-muted mb-6">{message}</p>
            <button
              onClick={() => navigate('/planos')}
              className="w-full py-3 rounded-lg font-semibold text-white"
              style={{ background: 'linear-gradient(90deg, #A855F7, #6366F1)' }}
            >
              Ver planos novamente
            </button>
          </>
        )}
      </div>
    </div>
  )
}