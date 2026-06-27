/**
 * AYRIA - Chat Store
 */
import { create } from 'zustand'
import { chatApi, Chat, Message } from '../lib/api'

interface ChatState {
  chats: Chat[]
  currentChatId: string | null
  messages: Message[]
  loading: boolean
  sending: boolean

  loadChats: () => Promise<void>
  createChat: () => Promise<string>
  loadMessages: (chatId: string) => Promise<void>
  sendMessage: (content: string) => Promise<void>
  deleteChat: (chatId: string) => Promise<void>
}

export const useChat = create<ChatState>((set, get) => ({
  chats: [],
  currentChatId: null,
  messages: [],
  loading: false,
  sending: false,

  loadChats: async () => {
    set({ loading: true })
    try {
      const { data } = await chatApi.listChats()
      set({ chats: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  createChat: async () => {
    const { data } = await chatApi.createChat()
    set({ chats: [data, ...get().chats], currentChatId: data.id, messages: [] })
    return data.id
  },

  loadMessages: async (chatId) => {
    set({ loading: true, currentChatId: chatId })
    try {
      const { data } = await chatApi.listMessages(chatId)
      set({ messages: data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  sendMessage: async (content) => {
    set({ sending: true })
    // Adiciona mensagem otimista do user
    const userMsg: Message = {
      id: 'temp-' + Date.now(),
      chat_id: get().currentChatId || '',
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    set({ messages: [...get().messages, userMsg] })

    try {
      const { data } = await chatApi.sendMessage(content, get().currentChatId || undefined)
      // Atualiza lista de chats e troca currentChatId se necessário
      if (!get().currentChatId) {
        set({ currentChatId: data.chat_id })
        get().loadChats()
      } else {
        get().loadChats()
      }
      // Substitui msg temp + adiciona resposta
      set({
        messages: [
          ...get().messages.filter((m) => m.id !== userMsg.id),
          userMsg,
          data,
        ],
        sending: false,
      })
    } catch (e) {
      set({ sending: false, messages: get().messages.filter((m) => m.id !== userMsg.id) })
    }
  },

  deleteChat: async (chatId) => {
    await chatApi.deleteChat(chatId)
    set({
      chats: get().chats.filter((c) => c.id !== chatId),
      currentChatId: get().currentChatId === chatId ? null : get().currentChatId,
      messages: get().currentChatId === chatId ? [] : get().messages,
    })
  },
}))
