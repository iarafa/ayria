/**
 * AYRIA - Sidebar (histórico + nova conversa + perfil)
 */
import { Plus, MessageCircle, LogOut, Shield, Trash2, Zap } from 'lucide-react'
import { useAuth } from '../store/auth'
import { useChat } from '../store/chat'
import { LogoIcon } from './Logo'
import { useNavigate } from 'react-router-dom'

export function Sidebar() {
  const { user, logout } = useAuth()
  const { chats, currentChatId, loadMessages, createChat, deleteChat } = useChat()
  const navigate = useNavigate()

  // ============ CRÉDITOS (FAKE por enquanto) ============
  // TODO: integrar com API real de consumo (tokens, créditos, plano)
  const creditsUsed = 23
  const creditsTotal = 100
  const creditsPercent = (creditsUsed / creditsTotal) * 100

  return (
    <aside
      className="w-[260px] h-screen bg-ayria-card border-r border-ayria-border flex flex-col"
      style={{ background: '#111111' }}
    >
      {/* Header com logo */}
      <div className="p-4 border-b border-ayria-border">
        <LogoIcon size={32} variant="circular" />
      </div>

      {/* Nova conversa */}
      <div className="p-4">
        <button
          onClick={async () => {
            await createChat()
          }}
          className="w-full py-3 px-4 rounded-xl font-semibold text-white flex items-center justify-center gap-2 transition-opacity hover:opacity-90"
          style={{
            background: 'linear-gradient(135deg, #6366F1, #A855F7)',
          }}
        >
          <Plus size={18} />
          Nova Conversa
        </button>
      </div>

      {/* Lista de conversas */}
      <div className="flex-1 overflow-y-auto px-2">
        <div className="text-xs text-ayria-muted px-3 py-2 uppercase tracking-wider">
          Conversas
        </div>
        {chats.length === 0 && (
          <div className="px-3 py-4 text-sm text-ayria-muted">
            Nenhuma conversa ainda.
          </div>
        )}
        {chats.map((chat) => (
          <div
            key={chat.id}
            className={`group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer mb-1 transition-colors ${
              currentChatId === chat.id
                ? 'bg-[#1E1E2E] text-ayria-text'
                : 'text-ayria-muted hover:bg-[#1a1a1a]'
            }`}
            onClick={() => loadMessages(chat.id)}
          >
            <MessageCircle size={14} />
            <span className="flex-1 truncate text-sm">{chat.title || 'Conversa'}</span>
            <button
              onClick={(e) => {
                e.stopPropagation()
                if (confirm('Deletar conversa?')) deleteChat(chat.id)
              }}
              className="opacity-0 group-hover:opacity-100 text-red-400 hover:text-red-300"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      {/* Perfil + ações */}
      <div className="p-4 border-t border-ayria-border space-y-3">
        {/* CRÉDITOS — consumo da ferramenta (FAKE por enquanto) */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-1.5">
              <Zap size={12} className="text-ayria-primary" />
              <span className="text-xs font-semibold text-ayria-text">Créditos</span>
            </div>
            <span className="text-xs text-ayria-muted">
              {creditsUsed}/{creditsTotal}
            </span>
          </div>
          <div
            className="w-full h-2 rounded-full overflow-hidden"
            style={{ background: '#1E1E2E' }}
          >
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${creditsPercent}%`,
                background: 'linear-gradient(90deg, #6366F1, #A855F7)',
                boxShadow: '0 0 8px rgba(99, 102, 241, 0.5)',
              }}
            />
          </div>
        </div>

        {(user?.role === 'admin' || user?.role === 'SUPER_ADMIN') && (
          <button
            onClick={() => navigate('/admin')}
            className="w-full py-2 px-3 rounded-lg text-sm flex items-center gap-2 text-ayria-admin hover:bg-[#1a1a1a]"
          >
            <Shield size={16} />
            Admin
          </button>
        )}
      </div>
    </aside>
  )
}
