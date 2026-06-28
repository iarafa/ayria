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
  register: (email: string, password: string, fullName?: string) => Promise<boolean>
  logout: () => void
  loadUser: () => Promise<void>
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
      localStorage.setItem('ayria_token', data.access_token)
      set({ user: data.user, token: data.access_token, loading: false })
      return true
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao logar', loading: false })
      return false
    }
  },

  register: async (email, password, fullName) => {
    set({ loading: true, error: null })
    try {
      const { data } = await authApi.register({ email, password, full_name: fullName })
      localStorage.setItem('ayria_token', data.access_token)
      set({ user: data.user, token: data.access_token, loading: false })
      return true
    } catch (e: any) {
      set({ error: e.response?.data?.detail || 'Erro ao cadastrar', loading: false })
      return false
    }
  },

  logout: () => {
    localStorage.removeItem('ayria_token')
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
}))
