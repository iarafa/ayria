/**
 * Helper de roteamento pós-auth (19/07/2026).
 *
 * REGRA ABSOLUTA (Rafael): **admin NUNCA é direcionado pra /chat**.
 * Admin vai SEMPRE pra /admin. Para analisar/observar um user, usa o painel.
 * Pra conversar com a Alma, usa a aba "Supervisão" → "Chat com user X".
 *
 * REGRA (19/07/2026 18:43): **user SEMPRE precisa ter assinatura ativa antes de
 * acessar /chat**. Sem trial grátis. Cadastro → email verify → /planos → Stripe → /chat.
 *
 * Esse helper é a ÚNICA fonte de verdade de "pra onde ir depois de logar/cadastrar".
 * Todas as navegações devem usar `getHomeRoute(user)` em vez de hardcoded.
 */
import type { User } from './api'

export function isAdmin(user: User | null): boolean {
  return user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
}

/**
 * User precisa pagar (não tem assinatura ativa nem está em período de tolerância)?
 * billing_status ∈ {None, '', 'billing_not_enabled'} = precisa pagar
 */
export function needsPayment(user: User | null | undefined): boolean {
  if (!user) return false
  return !user.billing_status || user.billing_status === 'billing_not_enabled'
}

/**
 * Rota home do user baseado em role + billing + onboarding_status.
 *
 * - admin (SUPER_ADMIN/admin)     → /admin
 * - user sem pagamento            → /planos (precisa assinar)
 * - onboarding pending|undefined  → /onboarding (criar perfil primeiro)
 * - onboarding creating_profile   → /criando-perfil
 * - onboarding completed          → /chat
 */
export function getHomeRoute(user: User | null | undefined): string {
  if (!user) return '/login'

  if (isAdmin(user)) {
    // 🔒 Admin nunca cai em chat. Vai direto pro dashboard.
    return '/admin'
  }

  // User comum SEM assinatura → precisa pagar antes de tudo
  if (needsPayment(user)) {
    return '/planos'
  }

  switch (user.onboarding_status) {
    case 'completed':
      return '/chat'
    case 'creating_profile':
      return '/criando-perfil'
    case 'pending':
    case undefined:
    case null:
    default:
      return '/onboarding'
  }
}

/**
 * Onde redirecionar quando user NÃO autorizado tenta acessar rota privada.
 * - Tenta ir pra home dele
 * - Se não tem user ainda, /login
 */
export function getFallbackRoute(user: User | null | undefined): string {
  return getHomeRoute(user)
}