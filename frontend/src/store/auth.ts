/**
 * AYRIA - Auth Store (Zustand)
 */
import { create } from 'zustand'
import { authApi, User } from '../lib/api'

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null

  login: (email: string, password: string) => Promise<boolean>
  register: (email: string, password: string, fullName?: string, planSlug?: string) => Promise<boolean>
  logout: () => void
  loadUser: () => Promise<void>
  updateProfile: (data: { full_name?: string; avatar_url?: string }) => Promise<boolean>
  uploadAvatar: (file: File) => Promise<string | null>
}

/**
 * Decodifica o payload (segunda parte) de um JWT sem validar assinatura.
 * Usado só pra ler `sub` (user_id) — não é confiável p/ auth, só p/ UX.
 * Falha silenciosa retorna null.
 */
function decodeJwtSub(token: string | null): string | null {
  if (!token) return null
  try {
    const part = token.split('.')[1]
    if (!part) return null
    // Base64URL → Base64
    const b64 = part.replace(/-/g, '+').replace(/_/g, '/')
    const padded = b64 + '='.repeat((4 - (b64.length % 4)) % 4)
    const json = atob(padded)
    const payload = JSON.parse(json)
    return payload.sub || payload.user_id || null
  } catch {
    return null
  }
}

/**
 * Faz logout "profundo" com reload pra /login — usado quando troca de
 * IDENTIDADE (user_id diferente). Útil em modo "observador" onde admin
 * assume identidade de outro user temporariamente.
 */
function hardLogout() {
  localStorage.removeItem('ayria_token')
  localStorage.removeItem('ayria_refresh')
  try {
    if ('caches' in window) {
      // Limpa qualquer cache residual do SW do user anterior
      caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
    }
  } catch {}
  window.location.href = '/login'
}

export const useAuth = create<AuthState>((set) => ({
  user: null,
  token: localStorage.getItem('ayria_token'),
  loading: false,
  error: null,

  login: async (email, password) => {
    set({ loading: true, error: null })
    try {
      const { data } = await authApi.login({ email, password })
      const newToken = data.access_token

      // ✅ FIX: comparar por user_id (sub do JWT), não pelo token.
      // O token MUDAR é normal (renovação, TTL curto). O que importa é a IDENTIDADE.
      const oldToken = localStorage.getItem('ayria_token')
      const oldSub = decodeJwtSub(oldToken)
      const newSub = decodeJwtSub(newToken) || data.user?.id

      // SÓ força logout profundo se for um USER diferente do logado.
      // (Mesmo user, token diferente = renovação tranquila, segue o jogo)
      if (oldToken && oldSub && newSub && oldSub !== newSub) {
        hardLogout()
        return false
      }

      // Caminho feliz: só substitui o token e segue
      localStorage.setItem('ayria_token', newToken)
      if (data.refresh_token) localStorage.setItem('ayria_refresh', data.refresh_token)
      set({ user: data.user, token: newToken, loading: false })
      return true
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao logar', loading: false })
      return false
    }
  },

  register: async (email, password, fullName, planSlug) => {
    set({ loading: true, error: null })
    try {
      const { data } = await authApi.register({
        email,
        password,
        full_name: fullName,
        plan_slug: planSlug,
      })
      const newToken = data.access_token

      const oldToken = localStorage.getItem('ayria_token')
      const oldSub = decodeJwtSub(oldToken)
      const newSub = decodeJwtSub(newToken) || data.user?.id

      if (oldToken && oldSub && newSub && oldSub !== newSub) {
        hardLogout()
        return false
      }

      localStorage.setItem('ayria_token', newToken)
      if (data.refresh_token) localStorage.setItem('ayria_refresh', data.refresh_token)
      set({ user: data.user, token: newToken, loading: false })
      return true
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao cadastrar', loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('ayria_token')
    localStorage.removeItem('ayria_refresh')
    set({ user: null, token: null })
  },

  loadUser: async () => {
    try {
      const { data } = await authApi.me()
      set({ user: data })
    } catch {
      localStorage.removeItem('ayria_token')
      set({ user: null, token: null })
    }
  },

  updateProfile: async (data) => {
    try {
      const { data: updated } = await authApi.updateMe(data)
      set({ user: updated })
      return true
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao atualizar perfil' })
      return false
    }
  },

  uploadAvatar: async (file: File) => {
    try {
      const { data } = await authApi.uploadAvatar(file)
      set({ user: data })
      return data.avatar_url
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao enviar foto' })
      return null
    }
  },
}))
