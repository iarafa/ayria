/**
 * AYRIA - Observe User Page (Admin)
 *
 * Modo OBSERVADOR (read-only):
 * - Admin entra nesta rota pra ver chats/messages de um user específico
 * - MESMA tela visual do ChatPage (sidebar + mensagens)
 * - Mas input de enviar mensagem está DESABILITADO (read-only)
 * - Toda ação é registrada em audit_log no backend
 *
 * Responsivo:
 * - < 1024px: sidebar como drawer, abre via botão hambúrguer
 * - ≥ 1024px: sidebar fixa 280px
 */
import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useAuth } from '../store/auth'
import { adminApi } from '../lib/api'
import { LogoIcon } from '../components/Logo'
import { Eye, Send, ArrowLeft, Shield, MessageCircle, Lock, Menu, X, Cpu } from 'lucide-react'
import { MessageDebugModal } from '../components/MessageDebugModal'

interface Chat {
  id: string
  user_id: string
  title: string | null
  summary: string | null
  created_at: string
  last_message_at: string | null
  message_count: number
}

interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  ai_model?: string | null
  tokens_used?: number | null
  metadata?: any
  created_at: string
}

export function ObserveUserPage() {
  const { userId } = useParams<{ userId: string }>()
  const { user: admin, logout } = useAuth()
  const navigate = useNavigate()
  const messagesEndRef = useRef<HTMLDivElement>(null)
const messageRefs = useRef<Record<string, HTMLDivElement | null>>({})
const [searchParams] = useSearchParams()
const highlightMessageId = searchParams.get('msg')

  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [targetUser, setTargetUser] = useState<any>(null)
  const [chats, setChats] = useState<Chat[]>([])
  const [currentChatId, setCurrentChatId] = useState<string | null>(
    searchParams.get('chat') || null
  )
  const [messages, setMessages] = useState<Message[]>([])
  const [loadingUser, setLoadingUser] = useState(true)
  const [loadingChats, setLoadingChats] = useState(false)
  const [loadingMsgs, setLoadingMsgs] = useState(false)
  const [debugMessage, setDebugMessage] = useState<Message | null>(null)

  // Verifica que é admin
  useEffect(() => {
    if (admin && admin.role !== 'SUPER_ADMIN') {
      navigate('/chat')
    }
  }, [admin, navigate])

  // Carrega dados do user observado
  useEffect(() => {
    if (!userId || !admin) return
    setLoadingUser(true)
    adminApi.getUserDetails(userId)
      .then(({ data }) => setTargetUser(data))
      .catch((err) => {
        alert('Erro ao carregar usuário: ' + (err.response?.data?.detail || err.message))
        navigate('/admin')
      })
      .finally(() => setLoadingUser(false))
  }, [userId, admin, navigate])

  // Carrega lista de chats
  useEffect(() => {
    if (!userId) return
    setLoadingChats(true)
    adminApi.observeUserChats(userId)
      .then(({ data }) => {
        setChats(data)
        // Se vier ?chat=... na URL, seleciona ele; senão, primeiro chat
        if (data.length > 0 && !currentChatId) {
          const urlChat = searchParams.get('chat')
          const found = urlChat ? data.find((c: Chat) => c.id === urlChat) : null
          setCurrentChatId(found ? found.id : data[0].id)
        }
      })
      .catch((err) => alert('Erro ao listar chats: ' + (err.response?.data?.detail || err.message)))
      .finally(() => setLoadingChats(false))
  }, [userId])

  // Carrega mensagens do chat selecionado
  useEffect(() => {
    if (!userId || !currentChatId) return
    setLoadingMsgs(true)
    adminApi.observeUserMessages(userId, currentChatId)
      .then(({ data }) => setMessages(data))
      .catch((err) => alert('Erro ao listar mensagens: ' + (err.response?.data?.detail || err.message)))
      .finally(() => setLoadingMsgs(false))
  }, [userId, currentChatId])

  // Auto-scroll pra última msg
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Rola pra mensagem específica quando vier ?msg=<uuid> (link direto da supervisão)
  useEffect(() => {
    if (!highlightMessageId || messages.length === 0) return
    const el = messageRefs.current[highlightMessageId]
    if (el) {
      setTimeout(() => {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        el.style.transition = 'background 0.3s'
        el.style.background = 'rgba(239, 68, 68, 0.15)'
        setTimeout(() => {
          el.style.background = ''
        }, 2500)
      }, 100)
    }
  }, [messages, highlightMessageId])

  // ESC fecha drawer + lock body scroll
  useEffect(() => {
    if (!sidebarOpen) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setSidebarOpen(false)
    }
    window.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [sidebarOpen])

  // Selecionar chat fecha drawer em mobile
  const handleSelectChat = (chatId: string) => {
    setCurrentChatId(chatId)
    setSidebarOpen(false)
  }

  if (loadingUser || !admin) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#050505' }}>
        <div className="text-ayria-muted">Carregando modo observador...</div>
      </div>
    )
  }

  // ============ CONTEÚDO DA SIDEBAR (reutilizado em drawer + fixed) ============
  const sidebarContent = (
    <>
      {/* Header */}
      <div className="p-4 border-b flex items-center gap-3" style={{ borderColor: '#1E1E2E' }}>
        <LogoIcon size={28} variant="circular" />
        <span className="font-bold tracking-[0.2em] text-ayria-admin text-xs flex-1">
          OBSERVADOR
        </span>
        <button
          onClick={() => setSidebarOpen(false)}
          className="lg:hidden text-ayria-muted hover:text-ayria-text p-1"
          title="Fechar menu"
          aria-label="Fechar menu"
        >
          <X size={18} />
        </button>
      </div>

      {/* Info do user observado */}
      <div className="p-4 border-b" style={{ borderColor: '#1E1E2E' }}>
        <Link
          to="/admin"
          className="text-xs text-ayria-muted hover:text-ayria-text flex items-center gap-1 mb-3"
        >
          <ArrowLeft size={12} />
          Voltar ao painel admin
        </Link>
        <div
          className="px-3 py-2 rounded-lg flex items-center gap-2 mb-3"
          style={{ background: 'rgba(245, 158, 11, 0.15)', border: '1px solid rgba(245, 158, 11, 0.3)' }}
        >
          <Eye size={16} style={{ color: '#F59E0B' }} className="flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="text-xs font-bold uppercase tracking-wider" style={{ color: '#F59E0B' }}>
              Modo Observador
            </div>
            <div className="text-xs text-ayria-muted">Read-only</div>
          </div>
        </div>
        <div className="text-sm text-ayria-text font-semibold truncate">
          {targetUser?.full_name || targetUser?.email}
        </div>
        <div className="text-xs text-ayria-muted truncate">{targetUser?.email}</div>
        <div className="flex items-center gap-2 mt-2 text-xs text-ayria-muted flex-wrap">
          <span
            className="px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#A855F7' }}
          >
            {targetUser?.selected_plan_name || 'sem plano'}
          </span>
          <span>{targetUser?.credit_balance || 0} cr</span>
        </div>
      </div>

      {/* Lista de chats */}
      <div className="flex-1 overflow-y-auto p-2">
        <div className="text-xs text-ayria-muted px-2 py-1 mb-1">
          {chats.length} conversa(s)
        </div>
        {loadingChats ? (
          <div className="text-ayria-muted text-xs px-2 py-3">Carregando...</div>
        ) : chats.length === 0 ? (
          <div className="text-ayria-muted text-xs px-2 py-3">
            Nenhuma conversa encontrada.
          </div>
        ) : (
          chats.map((chat) => (
            <button
              key={chat.id}
              onClick={() => handleSelectChat(chat.id)}
              className="w-full text-left px-3 py-2 rounded-lg transition-colors hover:bg-[#1a1a1a]"
              style={{
                background: currentChatId === chat.id ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
                border: currentChatId === chat.id ? '1px solid rgba(99, 102, 241, 0.3)' : '1px solid transparent',
              }}
            >
              <div className="text-sm text-ayria-text truncate flex items-center gap-1.5">
                <MessageCircle size={12} className="flex-shrink-0" />
                {chat.title || '(sem título)'}
              </div>
              <div className="text-xs text-ayria-muted mt-0.5 ml-4">
                {chat.message_count} msgs ·{' '}
                {chat.last_message_at
                  ? new Date(chat.last_message_at).toLocaleDateString('pt-BR')
                  : 'sem mensagens'}
              </div>
            </button>
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t" style={{ borderColor: '#1E1E2E' }}>
        <div className="flex items-center gap-2 text-xs">
          <Shield size={12} className="text-ayria-primary flex-shrink-0" />
          <span className="text-ayria-muted truncate">
            Você: <strong className="text-ayria-text">{admin.email}</strong>
          </span>
        </div>
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="mt-2 w-full text-xs text-ayria-muted hover:text-red-400"
        >
          Sair
        </button>
      </div>
    </>
  )

  return (
    <div className="h-screen flex overflow-hidden" style={{ background: '#050505' }}>
      {/* ============ DRAWER (mobile/tablet, < 1024px) ============ */}
      <div
        className={`fixed inset-0 z-40 lg:hidden ${sidebarOpen ? 'pointer-events-auto' : 'pointer-events-none'}`}
        aria-hidden={!sidebarOpen}
      >
        <div
          className={`absolute inset-0 bg-black/60 transition-opacity duration-300 ${
            sidebarOpen ? 'opacity-100' : 'opacity-0'
          }`}
          onClick={() => setSidebarOpen(false)}
        />
        <aside
          className={`absolute left-0 top-0 h-full w-[280px] max-w-[85vw] flex flex-col border-r transform transition-transform duration-300 ease-out ${
            sidebarOpen ? 'translate-x-0' : '-translate-x-full'
          }`}
          style={{ background: '#0A0A0A', borderColor: '#1E1E2E' }}
        >
          {sidebarContent}
        </aside>
      </div>

      {/* ============ SIDEBAR FIXA (desktop, ≥ 1024px) ============ */}
      <aside
        className="hidden lg:flex w-[280px] flex-shrink-0 flex-col border-r"
        style={{ background: '#0A0A0A', borderColor: '#1E1E2E' }}
      >
        {sidebarContent}
      </aside>

      {/* ÁREA PRINCIPAL — mensagens (read-only) */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header do chat */}
        <header
          className="px-4 sm:px-6 py-3 sm:py-4 border-b flex items-center gap-2 sm:gap-3 flex-shrink-0"
          style={{ borderColor: '#1E1E2E', background: '#0A0A0A' }}
        >
          {/* Hambúrguer (mobile) */}
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 -ml-2 text-ayria-muted hover:text-ayria-text rounded-lg hover:bg-[#1a1a1a]"
            title="Abrir menu"
            aria-label="Abrir menu"
          >
            <Menu size={20} />
          </button>

          <div className="flex-1 min-w-0">
            <h2 className="text-base sm:text-lg font-bold text-ayria-text truncate">
              {chats.find((c) => c.id === currentChatId)?.title || 'Selecione uma conversa'}
            </h2>
            <div className="text-xs text-ayria-muted flex items-center gap-1.5 mt-0.5">
              <Lock size={10} className="flex-shrink-0" />
              <span className="truncate">Modo somente leitura</span>
            </div>
          </div>
        </header>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-4 sm:py-6">
          {loadingMsgs ? (
            <div className="text-ayria-muted text-center py-12">Carregando mensagens...</div>
          ) : !currentChatId ? (
            <div className="text-ayria-muted text-center py-12">
              <Eye size={48} className="mx-auto mb-3 opacity-30" />
              <div className="text-sm sm:text-base">
                Selecione uma conversa na sidebar pra ver as mensagens.
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="text-ayria-muted text-center py-12">
              Esta conversa ainda não tem mensagens.
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-4">
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  ref={(el) => {
                    if (el) messageRefs.current[msg.id] = el
                  }}
                  className="rounded-xl"
                >
                  <ObserverMessageBubble message={msg} onShowDebug={() => setDebugMessage(msg)} />
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input DESABILITADO — modo observador */}
        <div
          className="border-t px-3 sm:px-6 py-3 sm:py-4 flex-shrink-0"
          style={{ borderColor: '#1E1E2E', background: '#0A0A0A' }}
        >
          <div className="max-w-3xl mx-auto">
            <div
              className="flex items-center gap-2 sm:gap-3 rounded-2xl px-3 sm:px-4 py-2.5 sm:py-3"
              style={{
                background: 'rgba(245, 158, 11, 0.08)',
                border: '1px dashed rgba(245, 158, 11, 0.4)',
              }}
            >
              <Lock size={16} style={{ color: '#F59E0B' }} className="flex-shrink-0" />
              <div className="flex-1 text-xs sm:text-sm text-ayria-muted min-w-0">
                <strong style={{ color: '#F59E0B' }}>Modo observador ativo.</strong>{' '}
                <span className="hidden sm:inline">Visualizando conversas de</span>{' '}
                <strong className="text-ayria-text truncate">{targetUser?.email}</strong>
                <span className="hidden sm:inline"> como auditor. Envio bloqueado.</span>
              </div>
              <button
                disabled
                className="p-2 rounded-xl opacity-30 cursor-not-allowed flex-shrink-0"
                style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
                title="Envio desabilitado em modo observador"
              >
                <Send size={16} className="text-white" />
              </button>
            </div>
            <div className="text-xs text-ayria-muted mt-2 text-center hidden sm:block">
              Toda visualização é registrada em audit_log (LGPD).
            </div>
          </div>
        </div>
      </main>

      {/* Modal de debug/transparência — só pra admins */}
      {debugMessage && (
        <MessageDebugModal message={debugMessage} onClose={() => setDebugMessage(null)} />
      )}
    </div>
  )
}

// === Sub-componente: bolha de mensagem do observador ===
function ObserverMessageBubble({ message, onShowDebug }: { message: Message; onShowDebug: () => void }) {
  const isUser = message.role === 'user'
  const isSystem = message.role === 'system'

  if (isSystem) {
    return (
      <div className="flex justify-center">
        <div
          className="px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm max-w-md text-center"
          style={{
            background: 'rgba(245, 158, 11, 0.1)',
            border: '1px solid rgba(245, 158, 11, 0.3)',
            color: '#F59E0B',
          }}
        >
          🔔 {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div className="max-w-[85%] sm:max-w-[80%]">
        <div className="text-xs text-ayria-muted mb-1 px-2 flex flex-wrap items-center gap-x-2">
          <span>{isUser ? '👤 Usuário' : '🤖 AYRIA'}</span>
          {message.ai_model && !isUser && (
            <span className="opacity-60">· {message.ai_model}</span>
          )}
          <span className="opacity-60 text-[10px]">
            {new Date(message.created_at).toLocaleString('pt-BR')}
          </span>
          {!isUser && (
            <button
              onClick={onShowDebug}
              className="opacity-70 hover:opacity-100 text-xs px-2 py-0.5 rounded flex items-center gap-1 ml-auto"
              style={{
                background: 'rgba(168, 85, 247, 0.15)',
                color: '#A855F7',
                border: '1px solid rgba(168, 85, 247, 0.3)',
              }}
              title="Ver o que a IA viu: prompt, contexto interpretado, tokens..."
            >
              <Cpu size={10} />
              Ver contexto
            </button>
          )}
        </div>
        <div
          className="px-3 sm:px-4 py-2.5 sm:py-3 rounded-2xl text-sm whitespace-pre-wrap break-words"
          style={{
            background: isUser
              ? 'linear-gradient(135deg, #6366F1, #A855F7)'
              : '#111111',
            border: isUser ? 'none' : '1px solid #1E1E2E',
            color: '#FFFFFF',
          }}
        >
          {message.content}
        </div>

        {/* PAINEL DO ADMIN — mostra premissas ANTES da resposta (só observador) */}
        {!isUser && message.metadata && <AdminPremisePanel metadata={message.metadata} />}
        {message.tokens_used != null && !isUser && (
          <div className="text-xs text-ayria-muted mt-1 px-2 opacity-60 flex items-center gap-2">
            <span>tokens: {message.tokens_used}</span>
            {message.metadata?.tokens_input_estimated != null && (
              <span>· in: ~{message.metadata.tokens_input_estimated.toLocaleString('pt-BR')}</span>
            )}
            {message.metadata?.interpreted_context?.supervisor_quick_level &&
              message.metadata.interpreted_context.supervisor_quick_level !== 'NORMAL' && (
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] font-bold"
                  style={{
                    background:
                      message.metadata.interpreted_context.supervisor_quick_level === 'URGENCIA'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(245, 158, 11, 0.2)',
                    color:
                      message.metadata.interpreted_context.supervisor_quick_level === 'URGENCIA'
                        ? '#EF4444'
                        : '#F59E0B',
                  }}
                >
                  {message.metadata.interpreted_context.supervisor_quick_level === 'URGENCIA' ? '🚨' : '⚠️'}
                  {' '}
                  {message.metadata.interpreted_context.supervisor_quick_level}
                </span>
              )}
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================
// ADMIN PREMISE PANEL — mostra o que a IA entendeu/fez/consultou
// Só aparece no Observador (admin only). Antes da resposta da Ayria.
// ============================================================
function AdminPremisePanel({ metadata }: { metadata: any }) {
  if (!metadata || !metadata.prompt_architecture) return null

  const selected = metadata.selected_modules || []
  const flags = metadata.prompt_flags || {}
  const reason = metadata.prompt_reason || {}
  const ic = metadata.interpreted_context || {}
  const profile = metadata.profile_used || ic.profile_used
  const rag = ic.rag_used
  const ragPrev = ic.rag_preview || ''
  const memories = ic.memories_count ?? 0
  const supLevel = ic.supervisor_quick_level || flags.crise ? 'URGENCIA' : 'NORMAL'
  const tokens = metadata.tokens_input_estimated
  const constitutionSrc = metadata.constitution_source

  // formatar premissas em frases curtas
  const entendeu: string[] = []
  if (selected.length) {
    entendeu.push(`User pediu ajuda sobre: ${selected.join(', ')}.`)
  }
  if (flags.crise) entendeu.push(`Detectei sinais de risco/crise na mensagem.`)
  if (flags.tem_memoria && memories > 0) entendeu.push(`Lembrei de ${memories} memória(s) relevante(s) do user.`)
  if (flags.tem_numerologia) entendeu.push(`User tem perfil numerológico mapeado.`)
  if (flags.tem_astrologia) entendeu.push(`User tem mapa astral mapeado.`)
  if (flags.tem_spiritual) entendeu.push(`User declarou preferência espiritual — alinhei abordagem.`)
  if (flags.onboarding_pendente) entendeu.push(`User ainda em onboarding.`)
  if (flags.admin) entendeu.push(`Admin logado — habilitei módulo admin para ajustes.`)

  const consultou: string[] = []
  consultou.push('📋 Constituição base da Ayria')
  if (profile) consultou.push('👤 Perfil completo do user')
  if (rag && ragPrev) consultou.push(`🧠 RAG (${ragPrev.length} chars de conhecimento relevante)`)
  if (memories > 0) consultou.push(`💭 ${memories} memória(s) episódica(s)`)
  if (Object.keys(reason).length) consultou.push(`🔍 Raciocínio do classificador (ver detalhes)`)

  const fez: string[] = []
  if (flags.crise) fez.push('🚨 Apliquei protocolo de crise (recomendei CVV/SAMU no prompt)')
  fez.push(`✨ Selecionei ${selected.length} módulo(s) dinâmico(s)`)
  if (rag) fez.push('🧠 Ingeri contexto RAG no system prompt')
  fez.push(`💰 Estimativa de custo: ~${tokens || '?'} tokens de entrada`)

  const premissa = flags.crise
    ? 'Princípio da vida > qualquer outro objetivo. Recomendei ajuda profissional.'
    : flags.tem_spiritual
      ? 'Respeitei a preferência espiritual declarada — não contradisse.'
      : 'Acolhimento + autoconhecimento + perguntas reflexivas (não conselhos).'

  return (
    <details
      className="mt-2 mb-2 rounded-xl overflow-hidden text-xs"
      style={{ background: '#0a0a0a', border: '1px solid rgba(168, 85, 247, 0.3)' }}
    >
      <summary
        className="px-3 py-2 cursor-pointer flex items-center gap-2 select-none"
        style={{ background: 'rgba(168, 85, 247, 0.08)' }}
      >
        <span className="text-base">🧠</span>
        <span className="font-bold text-ayria-text">Painel do Admin — O que a IA fez</span>
        {flags.crise && (
          <span
            className="text-[10px] px-1.5 py-0.5 rounded font-bold"
            style={{ background: 'rgba(239, 68, 68, 0.2)', color: '#EF4444' }}
          >
            🚨 CRISE
          </span>
        )}
        {constitutionSrc?.includes('customizada') && (
          <span
            className="text-[10px] px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(168, 85, 247, 0.2)', color: '#A855F7' }}
          >
            Constituição custom
          </span>
        )}
      </summary>

      <div className="p-3 space-y-3">
        {/* ENTENDI */}
        <Section title="✅ O que entendi" icon="👁">
          {entendeu.length === 0 ? (
            <Empty>Mensagem corriqueira, sem contexto especial.</Empty>
          ) : (
            <ul className="space-y-1">
              {entendeu.map((p, i) => (
                <li key={i} className="text-ayria-text">• {p}</li>
              ))}
            </ul>
          )}
        </Section>

        {/* FIZ */}
        <Section title="⚡ O que fiz" icon="🛠">
          <ul className="space-y-1">
            {fez.map((p, i) => (
              <li key={i} className="text-ayria-text">• {p}</li>
            ))}
          </ul>
        </Section>

        {/* CONSULTEI */}
        <Section title="📚 Quem consultei" icon="🗂️">
          <ul className="space-y-1">
            {consultou.map((p, i) => (
              <li key={i} className="text-ayria-muted">• {p}</li>
            ))}
          </ul>
          {Object.keys(reason).length > 0 && (
            <details className="mt-2">
              <summary className="cursor-pointer text-ayria-muted hover:text-ayria-text text-[10px]">
                ▸ Por que esses módulos?
              </summary>
              <div className="mt-1 space-y-0.5">
                {Object.entries(reason).map(([k, v]: [string, any]) => (
                  <div key={k} className="text-ayria-muted">
                    <span className="font-mono px-1 rounded" style={{ background: '#1E1E2E' }}>{k}</span>: {String(v)}
                  </div>
                ))}
              </div>
            </details>
          )}
        </Section>

        {/* PREMISSA */}
        <Section title="🎯 Premissa" icon="💡">
          <div className="text-ayria-text italic">{premissa}</div>
        </Section>

        {/* SUPERVISOR */}
        {supLevel && supLevel !== 'NORMAL' && (
          <Section title="🛡️ Supervisor" icon="🚨">
            <div
              className="px-2 py-1 rounded inline-block font-bold text-[11px]"
              style={{
                background: supLevel === 'URGENCIA' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)',
                color: supLevel === 'URGENCIA' ? '#EF4444' : '#F59E0B',
              }}
            >
              {supLevel === 'URGENCIA' ? '🚨 URGÊNCIA' : '⚠️ ATENÇÃO'}
            </div>
          </Section>
        )}
      </div>
    </details>
  )
}

function Section({ title, icon, children }: any) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider text-ayria-muted mb-1">
        {icon} {title}
      </div>
      <div className="text-xs">{children}</div>
    </div>
  )
}

function Empty({ children }: any) {
  return <div className="text-ayria-muted italic">{children}</div>
}
