/**
 * AYRIA - Chat Page (principal)
 */
import { useEffect } from 'react'
import { Sidebar } from '../components/Sidebar'
import { MessageBubble, TypingIndicator } from '../components/MessageBubble'
import { MessageInput } from '../components/MessageInput'
import { UserAvatar } from '../components/UserAvatar'
import { useChat } from '../store/chat'
import { useAuth } from '../store/auth'

export function ChatPage() {
  const { messages, sending, sendMessage, loadChats } = useChat()
  const { user } = useAuth()

  useEffect(() => {
    loadChats()
  }, [])

  // Saudação personalizada baseada na hora
  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return 'Bom dia'
    if (h < 18) return 'Boa tarde'
    return 'Boa noite'
  })()

  const userName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'você'

  return (
    <div className="h-screen flex" style={{ background: '#050505' }}>
      <Sidebar />

      {/* Área principal */}
      <main className="flex-1 flex flex-col">
        {/* Header — AGORA mostra foto + nome do USUÁRIO (não mais o logo AYRIA) */}
        <header className="glass px-6 py-4 flex items-center gap-3">
          <UserAvatar
            src={user?.avatar_url}
            name={user?.full_name}
            email={user?.email}
            size={56}
          />
          <div>
            <div className="font-semibold text-ayria-text">
              {user?.full_name || user?.email?.split('@')[0] || 'Você'}
            </div>
            <div className="text-xs text-ayria-success flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
              Conversando com AYRIA
            </div>
          </div>
        </header>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <h2 className="text-3xl font-bold mb-3 gradient-text">
                  {greeting}, {userName}
                </h2>
                <p className="text-ayria-muted max-w-md">
                  Estou aqui pra te ajudar a se conhecer melhor. Pode me contar o que
                  quiser — sobre seus sentimentos, sonhos, dúvidas. A conversa é sua.
                </p>
                <p className="text-ayria-muted/60 text-sm mt-6">
                  Comece digitando algo abaixo ↓
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
