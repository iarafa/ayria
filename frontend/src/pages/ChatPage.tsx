/**
 * AYRIA - Chat Page (principal)
 */
import { useEffect } from 'react'
import { Sidebar } from '../components/Sidebar'
import { MessageBubble, TypingIndicator } from '../components/MessageBubble'
import { MessageInput } from '../components/MessageInput'
import { Logo, LogoIcon } from '../components/Logo'
import { useChat } from '../store/chat'

export function ChatPage() {
  const { messages, sending, sendMessage, loadChats } = useChat()

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
          <LogoIcon size={40} variant="circular" />
          <div>
            <div className="font-semibold text-ayria-text">AYRIA</div>
            <div className="text-xs text-ayria-success flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block"></span>
              Online · pronta pra conversar
            </div>
          </div>
        </header>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-6">
          <div className="max-w-3xl mx-auto">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-20">
                <div className="mb-6 glow">
                  <LogoIcon size={120} variant="circular" />
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
