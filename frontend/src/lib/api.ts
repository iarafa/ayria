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

// API methods
export const authApi = {
  register: (data: { email: string; password: string; full_name?: string }) =>
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
}

export const onboardingApi = {
  status: () => api.get('/api/onboarding/status'),
  answer: (data: { question_step: number; attribute_code?: string; value: any }) =>
    api.post('/api/onboarding/answer', data),
}

export const chatApi = {
  listChats: () => api.get<Chat[]>('/api/chats'),
  createChat: (title?: string) => api.post('/api/chats', { title }),
  listMessages: (chatId: string) => api.get<Message[]>(`/api/chats/${chatId}/messages`),
  deleteChat: (chatId: string) => api.delete(`/api/chats/${chatId}`),
  sendMessage: (content: string, chatId?: string) =>
    api.post<Message>('/api/chat/message', { content, chat_id: chatId }),
}

export const adminApi = {
  listUsers: () => api.get('/api/admin/users'),
  createUser: (data: { email: string; password: string; full_name?: string; role?: string }) =>
    api.post('/api/admin/users', data),
  updateUser: (userId: string, data: { full_name?: string; is_active?: boolean }) =>
    api.put(`/api/admin/users/${userId}`, data),
  deleteUser: (userId: string) =>
    api.delete(`/api/admin/users/${userId}`),
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
}
