/**
 * AYRIA - API Client (axios)
 */
import axios from 'axios'
import { logError } from './logClient'

const API_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Adiciona token automaticamente
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('ayria_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 🆕 SECURITY: auto-refresh em 401 (token expirado)
let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb)
}

function onTokenRefreshed(newToken: string) {
  refreshSubscribers.forEach((cb) => cb(newToken))
  refreshSubscribers = []
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    // Só tenta refresh se for 401 E não for a prória rota de login/register/refresh
    if (
      error.response?.status === 401 &&
      !original._retry &&
      !original.url?.includes('/api/auth/login') &&
      !original.url?.includes('/api/auth/register') &&
      !original.url?.includes('/api/auth/refresh')
    ) {
      const refreshToken = localStorage.getItem('ayria_refresh')
      if (!refreshToken) {
        // Sem refresh, deixa o user cair no login
        localStorage.removeItem('ayria_token')
        return Promise.reject(error)
      }

      if (isRefreshing) {
        // Já tem um refresh em andamento — espera
        return new Promise((resolve) => {
          subscribeTokenRefresh((newToken) => {
            original.headers.Authorization = `Bearer ${newToken}`
            resolve(api(original))
          })
        })
      }

      original._retry = true
      isRefreshing = true

      try {
        const { data } = await axios.post(
          `${API_URL}/api/auth/refresh`,
          { refresh_token: refreshToken },
        )
        localStorage.setItem('ayria_token', data.access_token)
        if (data.refresh_token) localStorage.setItem('ayria_refresh', data.refresh_token)
        isRefreshing = false
        onTokenRefreshed(data.access_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch (refreshErr) {
        isRefreshing = false
        // Refresh falhou — força logout
        localStorage.removeItem('ayria_token')
        localStorage.removeItem('ayria_refresh')
        window.location.href = '/login'
        return Promise.reject(refreshErr)
      }
    }

    // 🆕 LOG AUTOMÁTICO: erros 4xx/5xx vão pro log do backend
    // (exceto /api/admin/log/event — evita loop se o próprio log falha)
    if (
      error.response?.status &&
      error.response.status >= 400 &&
      !original.url?.includes('/api/admin/log/event')
    ) {
      logError('axios', `${error.config?.method?.toUpperCase()} ${original.url}`, `HTTP ${error.response.status}`, {
        status: error.response.status,
        data: error.response.data,
        params: error.config?.params,
      })
    }

    return Promise.reject(error)
  },
)

// Tipos
export interface User {
  id: string
  email: string
  full_name?: string
  avatar_url?: string | null
  role: string
  onboarding_status: string
  numerology_data?: any
  billing_status?: string | null
  billing_provider?: string | null
  external_customer_id?: string | null
  external_subscription_id?: string | null
  is_verified?: boolean
  is_active?: boolean
  selected_plan_id?: string | null
  credit_balance?: number
  blocked_until?: string | null
}

export interface Chat {
  id: string
  title?: string
  summary?: string
  last_message_at: string
  message_count: number
}

export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  ai_model?: string
  tokens_used?: number
  created_at: string
  metadata?: any
}

export interface OnboardingQuestion {
  step: number
  question_text: string
  helper_text?: string
  question_type: string
  attribute_code?: string
  options?: any
}

export interface PendingQuestion {
  attribute_code: string
  question_text: string
  helper_text?: string
  question_type: string
  status: string
  last_asked_at?: string | null
  snooze_until?: string | null
}

// API methods
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string; plan_slug?: string }) =>
    api.post('/api/auth/register', data),
  login: (data: { email: string; password: string }) =>
    api.post('/api/auth/login', data),
  me: () => api.get('/api/auth/me'),
  updateMe: (data: { full_name?: string; avatar_url?: string }) =>
    api.patch('/api/auth/me', data),
  uploadAvatar: (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post('/api/auth/me/avatar', fd, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  // 🆕 SECURITY: refresh + troca de senha
  refresh: (refresh_token: string) =>
    api.post('/api/auth/refresh', { refresh_token }),
  changePassword: (old_password: string, new_password: string) =>
    api.patch('/api/auth/me/password', { old_password, new_password }),
}

export const onboardingApi = {
  status: () => api.get('/api/onboarding/status'),
  pending: () => api.get('/api/onboarding/pending'),
  answer: (data: { question_step: number; attribute_code?: string; value: any; action?: 'answer' | 'skip' | 'later' | 'continue_without' | 'snooze'; snooze_hours?: number }) =>
    api.post('/api/onboarding/answer', data),
  respondPending: (attributeCode: string, value: any) =>
    api.post(`/api/onboarding/pending/${attributeCode}/respond`, { question_step: 0, attribute_code: attributeCode, value }),
  skipPending: (attributeCode: string) =>
    api.post(`/api/onboarding/pending/${attributeCode}/skip`),
  snoozePending: (attributeCode: string, hours: number = 24) =>
    api.post(`/api/onboarding/pending/${attributeCode}/snooze?hours=${hours}`),
}

export const chatApi = {
  listChats: () => api.get<Chat[]>('/api/chats'),
  createChat: (title?: string) => api.post('/api/chats', { title }),
  listMessages: (chatId: string) => api.get<Message[]>(`/api/chats/${chatId}/messages`),
  deleteChat: (chatId: string) => api.delete(`/api/chats/${chatId}`),
  updateChat: (chatId: string, title: string) =>
    api.patch<Chat>(`/api/chats/${chatId}`, { title }),
  sendMessage: (content: string, chatId?: string) =>
    api.post<Message>('/api/chat/message', { content, chat_id: chatId }),
}

export const adminApi = {
  listUsers: (params?: { role?: string }) => api.get('/api/admin/users', { params }),
  createUser: (data: { email: string; password: string; full_name?: string; role?: string; plan_slug?: string }) =>
    api.post('/api/admin/users', data),
  updateUser: (userId: string, data: { full_name?: string; is_active?: boolean; selected_plan_slug?: string }) =>
    api.put(`/api/admin/users/${userId}`, data),
  deleteUser: (userId: string) =>
    api.delete(`/api/admin/users/${userId}`),
  blockUser: (userId: string, data: { duration: '1h' | '24h' | 'permanent' | 'unblock'; reason?: string }) =>
    api.post(`/api/admin/users/${userId}/block`, data),
  changeUserPassword: (userId: string, data: { new_password: string; reason?: string }) =>
    api.post(`/api/admin/users/${userId}/password`, data),
  getSupervisorKeywords: () => api.get('/api/admin/supervisor/keywords'),
  getSupervisorKeywordsSource: () =>
    api.get('/api/admin/supervisor/keywords/source'),
  saveSupervisorKeywordsSource: (content: string) =>
    api.put('/api/admin/supervisor/keywords/source', { content }),
  restoreSupervisorKeywordsDefault: () =>
    api.post('/api/admin/supervisor/keywords/restore-default', {}),
  // 🆕 08/07/2026 — chat trancado por categoria de keywords
  chatKeywordBlock: (category: string, messages: { role: string; content: string }[]) =>
    api.post(`/api/admin/supervisor/keywords/${encodeURIComponent(category)}/chat`, { messages }),
  applyKeywordBlock: (category: string, payload: { keywords_to_add?: string[]; keywords_to_remove?: string[] }) =>
    api.post(`/api/admin/supervisor/keywords/${encodeURIComponent(category)}/apply`, {
      keywords_to_add: payload.keywords_to_add || [],
      keywords_to_remove: payload.keywords_to_remove || [],
    }),
  adjustCredits: (data: { user_id: string; amount: number; description: string; type?: string }) =>
    api.post('/api/admin/credits/adjust', data),
  listPlans: () => api.get('/api/admin/plans'),
  updatePlan: (planId: string, data: { name?: string; credits?: number; price_brl?: number; active?: boolean }) =>
    api.put(`/api/admin/plans/${planId}`, data),
  getUserDetails: (userId: string) => api.get(`/api/admin/users/${userId}/details`),
  // Modo observador (read-only) — admin lê chats/msgs de outro user
  observeUserChats: (userId: string) => api.get(`/api/admin/users/${userId}/chats`),
  observeUserMessages: (userId: string, chatId: string) =>
    api.get(`/api/admin/users/${userId}/chats/${chatId}/messages`),
  listAttributes: () => api.get('/api/admin/attributes'),
  createAttribute: (data: any) => api.post('/api/admin/attributes', data),
  getOnboardingConfig: () => api.get('/api/admin/onboarding/config'),
  updateOnboardingConfig: (items: any[]) =>
    api.put('/api/admin/onboarding/config', items),
  listDocuments: () => api.get('/api/admin/knowledge/list'),
  uploadDocument: (formData: FormData) =>
    api.post('/api/admin/knowledge/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  deleteDocument: (id: string) => api.delete(`/api/admin/knowledge/${id}`),

  // ===== SUPERVISOR =====
  getSupervisionDashboard: () => api.get('/api/admin/supervisor/dashboard'),
  listAlerts: (params?: { status?: string; level?: string; risk_sublevel?: number; limit?: number; offset?: number }) => {
    const search = params ? '?' + new URLSearchParams(
      Object.fromEntries(Object.entries(params).map(([k,v]) => [k, String(v ?? '')]))
    ).toString() : ''
    return api.get(`/api/admin/supervisor/alerts${search}`)
  },
  acknowledgeAlert: (alertId: string, notes?: string) =>
    api.post(`/api/admin/supervisor/alerts/${alertId}/acknowledge`, { notes }),
  resolveAlert: (alertId: string, notes?: string) =>
    api.post(`/api/admin/supervisor/alerts/${alertId}/resolve`, { notes }),
  dismissAlert: (alertId: string, notes?: string) =>
    api.post(`/api/admin/supervisor/alerts/${alertId}/dismiss`, { notes }),
  getUserAnalyses: (userId: string, params?: { level?: string; limit?: number }) => {
    const search = params ? '?' + new URLSearchParams(params as any).toString() : ''
    return api.get(`/api/admin/supervisor/users/${userId}/analyses${search}`)
  },
  getUserTimeline: (userId: string) =>
    api.get(`/api/admin/supervisor/users/${userId}/timeline`),

  // Prompt do Supervisor (separado dos módulos da Ayria!)
  getSupervisorPrompt: () => api.get('/api/admin/supervisor/prompt'),
  updateSupervisorPrompt: (data: { content: string; description?: string }) =>
    api.put('/api/admin/supervisor/prompt', data),
  restoreSupervisorPrompt: () => api.post('/api/admin/supervisor/prompt/restore-default'),

  // ===== ALMA — arquitetura cognitiva modular (constituição + módulos) =====
  getPromptSystem: () => api.get('/api/admin/prompt/system'),
  updatePromptSystem: (data: { content: string; description?: string; key?: string }) =>
    api.put('/api/admin/prompt/system', data),
  restoreDefaultPrompt: (key?: string) =>
    api.post('/api/admin/prompt/system/restore-default', key ? { key } : {}),
  listAvailableModules: () => api.get('/api/admin/prompt/modules/available'),

  // RAG — indexação dos .md no Qdrant
  getPromptRagStatus: () => api.get('/api/admin/prompt/rag/status'),
  indexPromptsRag: (data: { source?: string; recreate?: boolean } = {}) =>
    api.post('/api/admin/prompt/rag/index', data),
  deletePromptRag: (data: { source: string }) =>
    api.post('/api/admin/prompt/rag/delete', data),

  // Debug — log do backend (admin only)
  debugLog: (params: { lines?: number; filter?: string; level?: string } = {}) =>
    api.get('/api/admin/debug/log', { params, responseType: 'text' }),
  debugLogInfo: () => api.get('/api/admin/debug/log/info'),

  // Prompt Chat — admin conversa COM contexto do MD carregado
  promptChat: (data: { key: string; user_message: string; history?: any[]; initial_context?: string }) =>
    api.post('/api/admin/prompt/chat', data),
  promptChatSave: (data: { key: string; new_content: string; reindex_rag?: boolean }) =>
    api.post('/api/admin/prompt/chat/save', data),

  // Delete module — remove arquivo + RAG + soft-delete config
  deletePromptModule: (module_key: string) =>
    api.delete(`/api/admin/prompt/module/${module_key}`),

  // ===== 🆕 08/07/2026 — SUB-ALMA POR USER =====
  // Backfill: gera pra todos os users sem sub-alma (skip admin). Retorna summary.
  backfillAllAlmas: () =>
    api.post('/api/admin/almas/backfill-all'),

  // Regenera nova versão (vai pra DRAFT, precisa aprovação)
  // Regenera nova versão (vai pra DRAFT, precisa aprovação)
  regenerateUserAlma: (userId: string) =>
    api.post(`/api/admin/users/${userId}/alma/regenerate`),
  // Lê alma ativa + draft pendente
  getUserAlma: (userId: string) =>
    api.get(`/api/admin/users/${userId}/alma`),
  // Aprova draft → active
  approveUserAlma: (userId: string) =>
    api.post(`/api/admin/users/${userId}/alma/approve`),
  // Rejeita draft → archived
  rejectUserAlma: (userId: string) =>
    api.post(`/api/admin/users/${userId}/alma/reject`),
  // Histórico de versões
  getUserAlmaHistory: (userId: string, limit = 5) =>
    api.get(`/api/admin/users/${userId}/alma/history?limit=${limit}`),
  // Rollback pra versão X
  rollbackUserAlma: (userId: string, version: number) =>
    api.post(`/api/admin/users/${userId}/alma/rollback/${version}`),

  // ===== 🆕 08/07/2026 — CHAT DE ANÁLISE POR USER =====
  // Chat IA trancado num user específico (NÃO consome créditos)
  chatUserAnalysis: (userId: string, messages: { role: string; content: string }[]) =>
    api.post(`/api/admin/users/${userId}/analysis/chat`, { messages }),
  // Salvar análise como nota persistente
  applyUserAnalysisNote: (
    userId: string,
    payload: {
      title: string
      content: string
      kind?: 'analysis' | 'observation' | 'action'
      conversation?: { role: string; content: string }[]
    },
  ) =>
    api.post(`/api/admin/users/${userId}/analysis/apply`, {
      title: payload.title,
      content: payload.content,
      kind: payload.kind || 'analysis',
      conversation: payload.conversation || [],
    }),
  // Listar notas do admin sobre o user
  listUserAnalysisNotes: (userId: string, limit = 50) =>
    api.get(`/api/admin/users/${userId}/analysis/notes?limit=${limit}`),
  // Apagar nota
  deleteUserAnalysisNote: (userId: string, noteId: string) =>
    api.delete(`/api/admin/users/${userId}/analysis/notes/${noteId}`),

  // ============== ADMINS (SystemAdminsTab) ==============
  listAdmins: () => api.get('/api/admin/admins'),
  createAdmin: (data: { email: string; password: string; full_name?: string; role?: string }) =>
    api.post('/api/admin/admins', data),
  updateAdmin: (adminId: string, data: { email?: string; full_name?: string; role?: string; is_active?: boolean }) =>
    api.put(`/api/admin/admins/${adminId}`, data),
  deleteAdmin: (adminId: string) =>
    api.delete(`/api/admin/admins/${adminId}`),
  resetAdminPassword: (adminId: string, data: { new_password: string }) =>
    api.post(`/api/admin/admins/${adminId}/password`, data),
}

// ============================================================
//  STRIPE — Checkout, Portal, Webhook
// ============================================================
export interface StripePlan {
  slug: string
  name: string
  credits: number
  tokens?: number
  price_brl: number
  price_id?: string
}

export interface StripeConfig {
  publishable_key: string
  app_url: string
  plans: StripePlan[]
}

export interface StripeActiveSubscription {
  id: string
  plan_slug: string
  plan_name: string
  status: string
  current_period_end: string | null
  cancel_at_period_end: boolean
  stripe_subscription_id: string
}

export interface StripeMySubscription {
  user_id: string
  billing_status: string
  billing_provider: string | null
  blocked_until: string | null
  credit_balance: number
  active_subscription: StripeActiveSubscription | null
  history: Array<{
    id: string
    plan_slug: string
    plan_name: string
    status: string
    created_at: string
  }>
}

export const stripeApi = {
  // GET /api/stripe/config — lista planos (público)
  getConfig: () => api.get<StripeConfig>('/api/stripe/config'),

  // GET /api/stripe/me — assinatura ativa do user logado
  getMySubscription: () =>
    api.get<StripeMySubscription>('/api/stripe/me'),

  // POST /api/stripe/create-checkout-session
  createCheckoutSession: (planSlug: string, couponCode?: string | null) =>
    api.post<{ session_id: string; url: string; plan_slug: string }>(
      '/api/stripe/create-checkout-session',
      { plan_slug: planSlug, coupon_code: couponCode || null },
    ),

  // POST /api/stripe/create-portal-session — gerenciar assinatura
  createPortalSession: () =>
    api.post<{ url: string }>('/api/stripe/create-portal-session'),
}

// ============================================================
//  COUPONS & PARTNERS
// ============================================================
export interface CouponValidateResponse {
  valid: boolean
  coupon_id?: string | null
  code?: string | null
  name?: string | null
  discount_type?: 'percent' | 'fixed' | null
  discount_value?: number | null
  applicable_plan_slug?: string | null
  duration_months?: number | null
  partner_name?: string | null
  preview?: { original_cents: number; discount_cents: number; final_cents: number } | null
  error?: string | null
}

export interface PartnerResponse {
  id: string
  name: string
  email: string
  phone?: string | null
  document_type?: string | null
  document_number?: string | null
  pix_key?: string | null
  commission_pct?: number | null
  notes?: string | null
  active: boolean
  created_at: string
  coupons_count: number
  total_commission_cents: number
}

export interface CouponResponse {
  id: string
  code: string
  stripe_coupon_id: string
  partner_id?: string | null
  partner_name?: string | null
  name?: string | null
  discount_type: 'percent' | 'fixed'
  discount_value: number
  applicable_plan_slug: string
  duration_months: number
  commission_pct: number
  max_redemptions?: number | null
  current_redemptions: number
  expires_at?: string | null
  active: boolean
  created_at: string
}

export interface CommissionReport {
  items: Array<{
    id: string
    coupon_code?: string | null
    partner_name?: string | null
    user_email?: string | null
    plan_slug: string
    original_amount_cents: number
    discount_amount_cents: number
    final_amount_cents: number
    commission_pct?: number | null
    commission_amount_cents?: number | null
    payout_status: string
    payout_at?: string | null
    created_at: string
  }>
  total_pending_cents: number
  total_paid_cents: number
  period_start?: string | null
  period_end?: string | null
}

export const couponsApi = {
  // POST /api/coupons/validate — público autenticado, valida cupom
  validate: (code: string, planSlug?: string) =>
    api.post<CouponValidateResponse>('/api/coupons/validate', {
      code,
      plan_slug: planSlug || null,
    }),

  // ====== ADMIN ======
  listPartners: () =>
    api.get<PartnerResponse[]>('/api/admin/partners'),
  createPartner: (data: Partial<PartnerResponse>) =>
    api.post<PartnerResponse>('/api/admin/partners', data),
  updatePartner: (partnerId: string, data: Partial<PartnerResponse>) =>
    api.patch<PartnerResponse>(`/api/admin/partners/${partnerId}`, data),
  deletePartner: (partnerId: string) =>
    api.delete(`/api/admin/partners/${partnerId}`).then(() => true),

  listCoupons: () =>
    api.get<CouponResponse[]>('/api/admin/coupons'),
  createCoupon: (data: any) =>
    api.post<CouponResponse>('/api/admin/coupons', data),
  updateCoupon: (couponId: string, data: any) =>
    api.patch<CouponResponse>(`/api/admin/coupons/${couponId}`, data),
  deactivateCoupon: (couponId: string) =>
    api.post<CouponResponse>(`/api/admin/coupons/${couponId}/deactivate`),

  listCommissions: (params?: { status?: string }) =>
    api.get<CommissionReport>('/api/admin/commissions', { params }),
  payCommission: (redemptionId: string) =>
    api.post(`/api/admin/commissions/${redemptionId}/pay`),
}
