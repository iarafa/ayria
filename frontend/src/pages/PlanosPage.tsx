/**
 * AYRIA - Planos Page (20/07/2026 23:00) + Cupom suporte
 *
 * Tela de planos Stripe. 3 tiers: Básico R$29,90/100, Intermediário R$59,90/500, Premium R$99,90/1000.
 *
 * 🎟️ Cupom de desconto:
 * - Input na parte de cima → busca via /api/coupons/validate
 * - Aplica desconto calculado em tempo real nos cards
 * - Auto-aplica via URL ?cupom=CODE
 * - Passa coupon_code no checkout session
 */
import { useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { stripeApi, couponsApi, StripeConfig, CouponValidateResponse } from '../lib/api'
import { useAuth } from '../store/auth'
import { LogoIcon } from '../components/Logo'

interface AppliedCoupon {
  code: string
  name: string
  discount_type: 'percent' | 'fixed'
  discount_value: number
  applicable_plan_slug: string
  preview: { original_cents: number; discount_cents: number; final_cents: number }
}

function applyCoupon(price_brl: number, coupon: AppliedCoupon): number {
  if (coupon.discount_type === 'percent') {
    return price_brl * (1 - coupon.discount_value / 100)
  }
  return Math.max(0, price_brl - coupon.discount_value)
}

export function PlanosPage() {
  const [config, setConfig] = useState<StripeConfig | null>(null)
  const [loading, setLoading] = useState(true)
  const [subscribing, setSubscribing] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const { user } = useAuth()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const deepLinkPlan = params.get('plan')

  // 🎟️ Cupom state
  const [couponInput, setCouponInput] = useState('')
  const [appliedCoupon, setAppliedCoupon] = useState<AppliedCoupon | null>(null)
  const [couponError, setCouponError] = useState<string | null>(null)
  const [validating, setValidating] = useState(false)

  useEffect(() => {
    stripeApi.getConfig()
      .then(r => { setConfig(r.data); setLoading(false) })
      .catch(e => { setError(`Erro ao carregar planos: ${e.message}`); setLoading(false) })
  }, [])

  // 🎯 Auto-aplica cupom via URL ?cupom=CODE
  useEffect(() => {
    const codeFromUrl = params.get('cupom')
    if (codeFromUrl && !appliedCoupon && config?.plans) {
      setCouponInput(codeFromUrl)
      validateCoupon(codeFromUrl)
      params.delete('cupom')
      navigate(`/planos?${params.toString()}`, { replace: true })
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config])

  async function validateCoupon(code?: string) {
    const c = (code || couponInput).trim().toUpperCase()
    if (!c) return
    setValidating(true)
    setCouponError(null)
    try {
      // Validar contra TODOS os planos (acha o plano certo do cupom)
      const res = await couponsApi.validate(c, 'premium')  // tenta premium primeiro
      const data: CouponValidateResponse = res.data
      if (!data.valid) {
        setCouponError(data.error || 'Cupom inválido')
        setAppliedCoupon(null)
        return
      }
      setAppliedCoupon({
        code: data.code!,
        name: data.name!,
        discount_type: data.discount_type as 'percent' | 'fixed', discount_value: data.discount_value!,
        applicable_plan_slug: data.applicable_plan_slug!,
        preview: data.preview!,
      })
      setCouponError(null)
    } catch (e: any) {
      setCouponError(e?.response?.data?.detail || e?.message || 'Erro ao validar cupom')
      setAppliedCoupon(null)
    } finally {
      setValidating(false)
    }
  }

  function removeCoupon() {
    setAppliedCoupon(null)
    setCouponInput('')
    setCouponError(null)
  }

  // Deep-link: se voltou do login com ?plan=basico, abre Stripe Checkout direto
  useEffect(() => {
    if (!user || !deepLinkPlan || !config?.plans) return
    const valid = config.plans.some(p => p.slug === deepLinkPlan)
    if (!valid) return
    params.delete('plan')
    navigate(`/planos?${params.toString()}`, { replace: true })
    handleSubscribe(deepLinkPlan)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, deepLinkPlan, config])

  const handleSubscribe = async (planSlug: string) => {
    if (!user) {
      navigate(`/login?next=${encodeURIComponent(`/planos?plan=${planSlug}${appliedCoupon ? `&cupom=${appliedCoupon.code}` : ''}`)}`)
      return
    }
    setSubscribing(planSlug)
    setError(null)
    try {
      const r = await stripeApi.createCheckoutSession(planSlug, appliedCoupon?.code)
      window.location.href = r.data.url
    } catch (e: any) {
      const msg = e?.response?.data?.detail || e?.message || 'Erro ao iniciar checkout'
      setError(msg)
      setSubscribing(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--ayria-bg)' }}>
        <div className="text-white text-lg">Carregando planos...</div>
      </div>
    )
  }

  if (error && !config) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--ayria-bg)' }}>
        <div className="text-red-400 text-center">
          <div className="text-xl mb-4">⚠️</div>
          <div>{error}</div>
        </div>
      </div>
    )
  }

  const plans = config?.plans || []

  // Cupom não compatível com este plano?
  const couponMismatch = (planSlug: string) =>
    appliedCoupon && appliedCoupon.applicable_plan_slug !== planSlug

  return (
    <div className="min-h-screen px-4 py-12" style={{ background: 'var(--ayria-bg)' }}>
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-8">
          <div className="flex justify-center mb-6">
            <LogoIcon size={280} variant="circular" className="max-w-[60vw]" />
          </div>
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
            Escolha seu plano
          </h2>
          <p className="text-ayria-muted text-lg max-w-2xl mx-auto">
            Acesse a Alma Numerológica e converse com a consciência de quem você é.
            Cancele quando quiser. Sem fidelidade.
          </p>
        </div>

        {/* 🎟️ Cupom de desconto */}
        <div className="max-w-md mx-auto mb-6">
          {appliedCoupon ? (
            <div className="flex items-center justify-between p-3 rounded-lg bg-green-900/20 border border-green-500/30">
              <div className="flex-1">
                <div className="text-green-400 font-bold text-sm">✓ Cupom {appliedCoupon.code} aplicado</div>
                <div className="text-green-300/70 text-xs">{appliedCoupon.name}</div>
              </div>
              <button onClick={removeCoupon} className="text-green-400 hover:text-white text-sm">Remover</button>
            </div>
          ) : (
            <div className="flex gap-2">
              <input
                type="text"
                value={couponInput}
                onChange={(e) => setCouponInput(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === 'Enter' && validateCoupon()}
                placeholder="Tem cupom? Digite aqui"
                className="flex-1 bg-slate-800 text-white rounded px-3 py-2 text-sm border border-slate-700 focus:border-amber-500 outline-none uppercase"
                data-testid="coupon-input"
              />
              <button
                onClick={() => validateCoupon()}
                disabled={!couponInput || validating}
                className="px-4 py-2 bg-amber-500 text-slate-900 font-medium rounded hover:bg-amber-400 disabled:opacity-50 text-sm"
              >
                {validating ? '...' : 'Aplicar'}
              </button>
            </div>
          )}
          {couponError && (
            <div className="mt-2 text-red-400 text-sm text-center">{couponError}</div>
          )}
        </div>

        {/* Erro inline */}
        {error && (
          <div className="max-w-md mx-auto mb-6 p-4 rounded-lg text-red-400 text-center"
            style={{ background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
            {error}
          </div>
        )}

        {/* Cards dos planos */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {plans.map((plan) => {
            const isPremium = plan.slug === 'premium'
            const isLoading = subscribing === plan.slug
            const mismatch = couponMismatch(plan.slug)
            const finalPrice = appliedCoupon && !mismatch
              ? applyCoupon(plan.price_brl, appliedCoupon)
              : plan.price_brl
            const hasDiscount = appliedCoupon && !mismatch && finalPrice < plan.price_brl

            return (
              <div
                key={plan.slug}
                data-testid={`plan-card-${plan.slug}`}
                className="rounded-2xl p-6 flex flex-col relative"
                style={{
                  background: isPremium
                    ? 'linear-gradient(135deg, rgba(168, 85, 247, 0.15), rgba(99, 102, 241, 0.15))'
                    : 'rgba(255, 255, 255, 0.03)', border: isPremium
                    ? '2px solid rgba(168, 85, 247, 0.5)' : '1px solid rgba(255, 255, 255, 0.1)', opacity: mismatch ? 0.5 : 1,
                }}
              >
                {isPremium && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 rounded-full text-xs font-bold text-white"
                    style={{ background: 'linear-gradient(90deg, #da950b, #f1c961)' }}>
                    MAIS POPULAR
                  </div>
                )}

                <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
                <div className="flex items-baseline gap-1 mb-4">
                  {hasDiscount && (
                    <span className="text-lg line-through text-slate-500">
                      R$ {plan.price_brl.toFixed(2).replace('.', ',')}
                    </span>
                  )}
                  <span className="text-4xl font-bold text-white">
                    R$ {finalPrice.toFixed(2).replace('.', ',')}
                  </span>
                  <span className="text-ayria-muted">/mês</span>
                </div>

                {hasDiscount && (
                  <div className="text-xs text-amber-400 mb-3 font-medium">
                    🎟️ -{appliedCoupon.discount_type === 'percent' ? `${appliedCoupon.discount_value}%` : `R$ ${appliedCoupon.discount_value.toFixed(2).replace('.', ',')}`} de desconto
                  </div>
                )}

                {mismatch && (
                  <div className="text-xs text-slate-500 mb-3">
                    (Cupom válido apenas para o plano {appliedCoupon.applicable_plan_slug})
                  </div>
                )}

                <div className="mb-6 pb-6 border-b" style={{ borderColor: 'rgba(255,255,255,0.1)' }}>
                  <div className="text-ayria-muted text-sm mb-1">Inclui</div>
                  <div className="text-white text-2xl font-bold">
                    {plan.tokens.toLocaleString('pt-BR')} <span className="text-sm font-normal text-ayria-muted">tokens</span>
                  </div>
                  <div className="text-ayria-muted text-xs mt-1">por mês</div>
                </div>

                <ul className="text-sm text-ayria-muted space-y-2 mb-6 flex-1">
                  <li className="flex gap-2"><span className="text-green-400">✓</span><span>Acesso à Alma Numerológica</span></li>
                  <li className="flex gap-2"><span className="text-green-400">✓</span><span>Mapa numerológico completo</span></li>
                  <li className="flex gap-2"><span className="text-green-400">✓</span><span>Conversas ilimitadas</span></li>
                  {plan.tokens >= 500 && <li className="flex gap-2"><span className="text-green-400">✓</span><span>Histórico estendido</span></li>}
                  {plan.tokens >= 1000 && <li className="flex gap-2"><span className="text-green-400">✓</span><span>Suporte prioritário</span></li>}
                </ul>

                <button
                  onClick={() => handleSubscribe(plan.slug)}
                  disabled={isLoading || !!subscribing || !!mismatch}
                  className="w-full py-3 rounded-lg font-semibold text-white transition disabled:opacity-50"
                  style={{
                    background: isPremium
                      ? 'linear-gradient(90deg, #da950b, #f1c961)'
                      : 'rgba(255, 255, 255, 0.08)', border: isPremium ? 'none' : '1px solid rgba(255, 255, 255, 0.15)' }}
                  data-testid={`subscribe-${plan.slug}`}
                >
                  {mismatch ? 'Cupom não válido' : isLoading ? 'Redirecionando...' : user ? 'Assinar agora' : 'Entrar e assinar'}
                </button>
              </div>
            )
          })}
        </div>

        <div className="text-center">
          <p className="text-ayria-muted text-sm">
            💳 Pagamento seguro processado pela Stripe. Cancele quando quiser.
          </p>
          {user && (
            <button onClick={() => navigate('/chat')} className="mt-4 text-ayria-muted hover:text-white text-sm underline">
              Voltar para o chat
            </button>
          )}
          {!user && (
            <button onClick={() => navigate('/login')} className="mt-4 text-ayria-muted hover:text-white text-sm underline">
              Já tem conta? Entrar
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
