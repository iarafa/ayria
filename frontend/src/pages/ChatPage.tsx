/**
 * AYRIA - Chat Page (principal)
 */
import { useEffect } from 'react'
import { Sidebar } from '../components/Sidebar'
import { MessageBubble, TypingIndicator } from '../components/MessageBubble'
import { MessageInput } from '../components/MessageInput'
import { Logo, LogoIcon } from '../components/Logo'
import { useChat } from '../store/chat'
import { useAuth } from '../store/auth'
import { LogOut, Shield } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export function ChatPage() {
  const { messages, sending, sendMessage, loadChats } = useChat()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  // Iniciais do usuário para avatar inline
  const userInitials = (() => {
    if (user?.full_name) {
      const parts = user.full_name.trim().split(/\s+/)
      if (parts.length >= 2) return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
      return user.full_name[0].toUpperCase()
    }
    if (user?.email) return user.email[0].toUpperCase()
    return '?'
  })()

  useEffect(() => {
    loadChats()
  }, [])

  return (
    <div className="h-screen flex" style={{ background: '#050505' }}>
      <Sidebar />

      {/* Área principal */}
      <main className="flex-1 flex flex-col">
        {/* Header com glassmorphism */}
        <header className="glass px-6 py-4 flex items-center gap-3">
          {/* Esquerda: logo AYRIA + título */}
          <div className="flex items-center gap-3">
            <LogoIcon size={56} variant="circular" />
            <div>
              <div className="font-semibold text-ayria-text">AYRIA</div>
              <div className="text-xs text-ayria-success flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
                Online · pronta pra conversar
              </div>
            </div>
          </div>

          {/* Direita: avatar + nome do user (MOVIDO do rodapé da sidebar) */}
          <div className="ml-auto flex items-center gap-3">
            {(user?.role === 'admin' || user?.role === 'SUPER_ADMIN') && (
              <button
                onClick={() => navigate('/admin')}
                className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition-colors hover:bg-[#1a1a1a]"
                style={{
                  background: 'rgba(245, 158, 11, 0.1)',
                  color: '#F59E0B',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
                title="Painel Admin"
              >
                <Shield size={14} />
                Admin
              </button>
            )}
            <div className="flex items-center gap-2">
              <div
                className="w-10 h-10 rounded-full flex items-center justify-center text-white font-semibold text-sm flex-shrink-0"
                style={{
                  background: user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
                    ? 'linear-gradient(135deg, #F59E0B, #EF4444)'
                    : 'linear-gradient(135deg, #6366F1, #A855F7)',
                  boxShadow: '0 0 12px rgba(99, 102, 241, 0.4)',
                  border: '2px solid rgba(99, 102, 241, 0.3)',
                }}
              >
                {userInitials}
              </div>
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold text-ayria-text truncate max-w-[150px]">
                  {user?.full_name || user?.email?.split('@')[0] || 'Você'}
                </div>
              </div>
            </div>
            <button
              onClick={logout}
              className="text-ayria-muted hover:text-red-400 transition-colors p-2"
              title="Sair"
            >
              <LogOut size={16} />
            </button>
          </div>
        </header>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <div className="mb-6 glow">
                  <LogoIcon size={160} variant="circular" />
                </div>
                <h2 className="text-2xl font-bold mb-2 gradient-text">
                  Olá, eu sou AYRIA
                </h2>
                <p className="text-ayria-muted max-w-md">
                  Estou aqui pra te ajudar a se conhecer melhor. Pode me contar o que
                  quiser — sobre seus sentimentos, sonhos, dúvidas. A conversa é sua.
                </p>
              </div>
            )}

            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                role={m.role}
                content={m.content}
                model={m.ai_model}
                tokens={m.tokens_used}
                thinking={m.metadata?.thinking ?? null}
              />
            ))}

            {sending && <TypingIndicator />}
          </div>
        </div>

        {/* Input */}
        <MessageInput onSend={sendMessage} disabled={sending} />
      </main>
    </div>
  )
}
