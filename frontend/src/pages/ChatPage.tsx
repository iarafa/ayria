/**
 * AYRIA - Chat Page (principal)
 *
 * Layout responsivo:
 * - < 1024px: Sidebar é drawer (controlado por `sidebarOpen`)
 *   Botão hambúrguer no header à esquerda
 * - ≥ 1024px: Sidebar fixa 260px sempre visível, sem hambúrguer
 *
 * Header:
 * - Esquerda: hambúrguer (mobile) + SLOT DE OPÇÕES DE CHAT (Quebrar, futuro toggle, etc)
 * - Direita: Admin (se admin) + avatar do user + logout
 * - SEM logo AYRIA no header (já existe na sidebar — duplicado removido em 29/06)
 */
import { useEffect, useRef, useState } from 'react'
import { Sidebar } from '../components/Sidebar'
import { MessageBubble, TypingIndicator, renderMarkdown } from '../components/MessageBubble'
import { MessageInput } from '../components/MessageInput'
import { ProfileEditModal } from '../components/ProfileEditModal'
import { ChangePasswordModal } from '../components/ChangePasswordModal'
import { SpiritualityPicker } from '../components/SpiritualityPicker'
import { useChat } from '../store/chat'
import { useAuth } from '../store/auth'
import { LogOut, Shield, Pencil, UserCircle, Menu, AlignJustify, ChevronsUpDown } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useAutoScroll } from '../hooks/useAutoScroll'
import { useLocalStorage } from '../hooks/useLocalStorage'

export function ChatPage() {
  const { messages, sending, sendMessage, loadChats } = useChat()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [editProfileOpen, setEditProfileOpen] = useState(false)
  const [changePasswordOpen, setChangePasswordOpen] = useState(false)

  // Listener: ProfileEditModal dispara evento pra abrir ChangePasswordModal
  useEffect(() => {
    const handler = () => setChangePasswordOpen(true)
    window.addEventListener('ayria:open-change-password', handler)
    return () => window.removeEventListener('ayria:open-change-password', handler)
  }, [])
  const [sidebarOpen, setSidebarOpen] = useState(false)
  // === Toggle global "Quebrar mensagens longas" (persiste em localStorage) ===
  const [collapseEnabled, setCollapseEnabled] = useLocalStorage<boolean>('ayria:collapse-messages', true)

  // Sistema 2: perguntas pendentes são perguntadas pela IA no campo de chat normal.
  // Removido o banner separado — Rafael pediu TUDO via chat.



  useEffect(() => {
    loadChats()
  }, [])

  // === Autoscroll inteligente ===
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const { scrollToBottomIfAtBottom, scrollToBottomInstant } = useAutoScroll(messagesContainerRef)
  const previousMessagesLengthRef = useRef(0)

  // Quando TypingIndicator aparece → scroll INSTANTÂNEO
  useEffect(() => {
    if (sending) scrollToBottomInstant()
  }, [sending, scrollToBottomInstant])

  // Quando nova mensagem chega (e não é typing) → scroll SMOOTH se user tava no fundo
  useEffect(() => {
    if (messages.length > previousMessagesLengthRef.current) {
      scrollToBottomIfAtBottom()
    }
    previousMessagesLengthRef.current = messages.length
  }, [messages.length, scrollToBottomIfAtBottom])

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: '#050505' }}>
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Área principal */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header com glassmorphism */}
        <header className="glass px-3 sm:px-6 py-3 sm:py-4 flex items-center gap-2 sm:gap-3 flex-shrink-0">
          {/* === SLOT DE OPÇÕES DE CHAT (esquerda) === */}
          {/* Aqui vão os toggles/ações do chat: hambúrguer (mobile), quebrar/inteiras, futuros toggles */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 -ml-1 text-ayria-muted hover:text-ayria-text rounded-lg hover:bg-[#1a1a1a] transition-colors"
            title="Abrir menu"
            aria-label="Abrir menu"
          >
            <Menu size={20} />
          </button>

          {/* Preferência de Vida — popover com lista de religiões */}
          <SpiritualityPicker />

          {/* TOGGLE: Quebrar/Inteiras — com label + descrição visíveis */}
          <button
            onClick={() => setCollapseEnabled((v) => !v)}
            className="flex flex-col items-center sm:flex-row sm:gap-2 px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg transition-colors hover:bg-[#1a1a1a]"
            style={{
              background: collapseEnabled
                ? 'rgba(99, 102, 241, 0.15)'
                : 'rgba(148, 163, 184, 0.08)',
              color: collapseEnabled ? '#A855F7' : '#94A3B8',
              border: collapseEnabled
                ? '1px solid rgba(168, 85, 247, 0.4)'
                : '1px solid rgba(148, 163, 184, 0.2)',
            }}
            title={collapseEnabled
              ? 'Mensagens longas estão sendo quebradas (Ver mais). Clique pra mostrar inteiras.'
              : 'Mostrando mensagens inteiras. Clique pra quebrar as longas (Ver mais).'}
            aria-pressed={collapseEnabled}
          >
            <div className="flex items-center gap-1.5">
              {collapseEnabled ? <AlignJustify size={14} /> : <ChevronsUpDown size={14} />}
              <span className="text-xs font-medium hidden sm:inline">
                {collapseEnabled ? 'Quebrar' : 'Inteiras'}
              </span>
            </div>
            <span className="text-[9px] sm:text-[10px] opacity-70 leading-tight mt-0.5 sm:mt-0 max-w-[100px] sm:max-w-none text-center sm:text-left">
              {collapseEnabled
                ? 'Respostas longas viram "Ver mais"'
                : 'Mostra todas as respostas completas'}
            </span>
          </button>

          {/* Direita: avatar + nome do user */}
          <div className="ml-auto flex items-center gap-2 sm:gap-3">
            {(user?.role === 'admin' || user?.role === 'SUPER_ADMIN') && (
              <button
                onClick={() => navigate('/admin')}
                className="flex flex-col items-center sm:flex-row sm:gap-2 px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg transition-colors hover:bg-[#1a1a1a]"
                style={{
                  background: 'rgba(245, 158, 11, 0.1)',
                  color: '#F59E0B',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
                title="Painel Admin"
              >
                <div className="flex items-center gap-1">
                  <Shield size={14} />
                  <span className="text-xs font-medium hidden sm:inline">Admin</span>
                </div>
                <span className="text-[9px] sm:text-[10px] opacity-70 leading-tight mt-0.5 sm:mt-0 max-w-[100px] sm:max-w-none text-center sm:text-left">
                  Painel administrativo
                </span>
              </button>
            )}
            <button
              onClick={() => setEditProfileOpen(true)}
              className="flex items-center gap-2 px-2 py-1 rounded-lg transition-colors hover:bg-[#1a1a1a] group"
              title="Editar perfil"
            >
              {user?.avatar_url ? (
                <img
                  src={user.avatar_url}
                  alt={user?.full_name || user?.email}
                  className="w-9 h-9 sm:w-10 sm:h-10 rounded-full object-cover flex-shrink-0 relative"
                  style={{
                    boxShadow: '0 0 12px rgba(99, 102, 241, 0.4)',
                    border: '2px solid rgba(99, 102, 241, 0.3)',
                  }}
                />
              ) : (
                <div
                  className="w-9 h-9 sm:w-10 sm:h-10 rounded-full flex items-center justify-center flex-shrink-0 relative"
                  style={{
                    background: user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
                      ? 'linear-gradient(135deg, #F59E0B, #EF4444)'
                      : 'linear-gradient(135deg, #6366F1, #A855F7)',
                    boxShadow: '0 0 12px rgba(99, 102, 241, 0.4)',
                    border: '2px solid rgba(99, 102, 241, 0.3)',
                  }}
                >
                  <UserCircle size={20} className="text-white sm:hidden" />
                  <UserCircle size={22} className="text-white hidden sm:block" />
                  <div
                    className="absolute inset-0 rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                    style={{ background: 'rgba(0, 0, 0, 0.5)' }}
                  >
                    <Pencil size={12} className="text-white" />
                  </div>
                </div>
              )}
              <div className="text-right hidden sm:block">
                <div className="text-sm font-semibold text-ayria-text truncate max-w-[150px]">
                  {user?.full_name || user?.email?.split('@')[0] || 'Você'}
                </div>
                <div className="text-xs text-ayria-muted/60 group-hover:text-ayria-primary transition-colors">
                  Editar perfil
                </div>
              </div>
            </button>
            <button
              onClick={logout}
              className="flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg text-ayria-muted hover:text-red-400 transition-colors hover:bg-[#1a1a1a]"
              title="Sair da conta"
            >
              <LogOut size={16} />
              <span className="text-[9px] sm:text-[10px] opacity-70 leading-tight hidden sm:block">
                Sair
              </span>
            </button>
          </div>
        </header>

        {/* Mensagens */}
        <div
          ref={messagesContainerRef}
          className="flex-1 overflow-y-auto px-3 sm:px-4 py-4 sm:py-6"
        >
          <div className="max-w-5xl mx-auto">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center py-12 sm:py-20">
                <p
                  className="text-ayria-muted max-w-md text-sm sm:text-base px-4"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown('Olá, eu sou AYRIA — estou aqui pra te ajudar a se conhecer melhor. Pode me contar o que quiser — sobre seus sentimentos, sonhos, dúvidas. A conversa é sua.') }}
                />
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
                collapseEnabled={collapseEnabled}
                isPendingQuestion={!!m.metadata?.is_pending_question}
                pendingAttrLabel={m.metadata?.pending_attr_label ?? null}
                timestamp={m.created_at}
              />
            ))}

            {sending && <TypingIndicator />}
          </div>
        </div>

        {/* Input */}
        <MessageInput onSend={sendMessage} disabled={sending} />
      </main>

      {/* Modal de edição de perfil */}
      <ProfileEditModal
        open={editProfileOpen}
        onClose={() => setEditProfileOpen(false)}
      />

      {/* 🆕 SECURITY: modal de troca de senha (aberto via evento custom) */}
      <ChangePasswordModal
        open={changePasswordOpen}
        onClose={() => setChangePasswordOpen(false)}
        onSuccess={() => {
          // Limpa tokens locais (mantém refresh_token pra permitir relogar)
          // Não força logout — user pode continuar usando com mesmo user
        }}
      />
    </div>
  )
}