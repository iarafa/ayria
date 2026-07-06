/**
 * AYRIA - API Client (axios)
 */
import axios from 'axios'

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
  listUsers: () => api.get('/api/admin/users'),
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

  // Prompt Chat — admin conversa COM contexto do MD carregado
  promptChat: (data: { key: string; user_message: string; history?: any[]; initial_context?: string }) =>
    api.post('/api/admin/prompt/chat', data),
  promptChatSave: (data: { key: string; new_content: string; reindex_rag?: boolean }) =>
    api.post('/api/admin/prompt/chat/save', data),

  // Delete module — remove arquivo + RAG + soft-delete config
  deletePromptModule: (module_key: string) =>
    api.delete(`/api/admin/prompt/module/${module_key}`),
}
