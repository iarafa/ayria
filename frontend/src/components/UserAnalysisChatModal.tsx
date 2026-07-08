/**
 * AYRIA - User Analysis Chat Modal (Admin) — 08/07/2026
 *
 * Clone do KeywordBlockChatModal aplicado a um USER específico:
 *  - Abre a partir do botão "🤖 Analisar com IA" no header da ObserveUserPage
 *  - Backend injeta system prompt focado NO USER (perfil, sub-alma, msgs, alertas, etc)
 *  - Chat com IA — admin interpreta o user (não fala com ele)
 *  - Quando IA responde com JSON {title, content, kind} → botão "💾 Salvar como nota"
 *  - Notas aparecem em user_supervisor_notes, visíveis só entre SUPER_ADMINs
 *
 * NÃO consome créditos (mesmo padrão do KeywordBlockChatModal)
 */
import { useEffect, useRef, useState } from 'react'
import { X, Send, Loader2, Sparkles, CheckCircle2, AlertTriangle, Lock, User, Save } from 'lucide-react'
import { adminApi } from '../lib/api'

interface Props {
  open: boolean
  userId: string | null
  firstName: string
  onClose: () => void
  onSaved?: () => void
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  ts: number
}

interface NoteProposal {
  title: string
  content: string
  kind: 'analysis' | 'observation' | 'action'
}

const KIND_LABEL: Record<string, { label: string; color: string; emoji: string }> = {
  analysis: { label: 'Análise', color: '#A855F7', emoji: '🧠' },
  observation: { label: 'Observação', color: '#3B82F6', emoji: '👁' },
  action: { label: 'Ação', color: '#F59E0B', emoji: '⚡' },
}

const GREETING = (firstName: string) =>
  `Olá! Posso ajudar a entender padrões do **${firstName}**, sugerir ações para o painel, ou resumir a situação atual dele. Estou exclusivamente focado no contexto deste usuário.`

function tryExtractNote(text: string): NoteProposal | null {
  const clean = text.replace(/```json\s*/gi, '').replace(/```/g, '').trim()
  const start = clean.indexOf('{')
  const end = clean.lastIndexOf('}')
  if (start === -1 || end === -1 || end < start) return null
  const jsonStr = clean.substring(start, end + 1)
  try {
    const data = JSON.parse(jsonStr)
    if (typeof data.title === 'string' && typeof data.content === 'string') {
      return {
        title: data.title.slice(0, 200),
        content: data.content,
        kind: (['analysis', 'observation', 'action'].includes(data.kind) ? data.kind : 'analysis') as NoteProposal['kind'],
      }
    }
  } catch {
    /* ignore */
  }
  return null
}

export function UserAnalysisChatModal({
  open,
  userId,
  firstName,
  onClose,
  onSaved,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [proposal, setProposal] = useState<NoteProposal | null>(null)
  const endRef = useRef<HTMLDivElement>(null)
  const convRef = useRef<{ role: 'user' | 'assistant'; content: string }[]>([])

  // Resetar quando abre
  useEffect(() => {
    if (open && userId) {
      const greeting = GREETING(firstName)
      setMessages([{ role: 'assistant', content: greeting, ts: Date.now() }])
      convRef.current = [{ role: 'assistant', content: greeting }]
      setInput('')
      setError(null)
      setSuccess(null)
      setProposal(null)
    }
  }, [open, userId, firstName])

  // ESC fecha
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open && !busy && !saving) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose, busy, saving])

  // auto-scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, busy])

  if (!open || !userId) return null

  async function send() {
    if (!input.trim() || busy || !userId) return
    const userMsg: ChatMessage = { role: 'user', content: input.trim(), ts: Date.now() }
    const nextMsgs = [...messages, userMsg]
    setMessages(nextMsgs)
    convRef.current.push({ role: 'user', content: userMsg.content })
    setInput('')
    setBusy(true)
    setError(null)
    setSuccess(null)
    setProposal(null)
    try {
      const { data } = await adminApi.chatUserAnalysis(userId, convRef.current)
      const aiContent = data?.message?.content || '(sem resposta da IA)'
      const aiMsg: ChatMessage = { role: 'assistant', content: aiContent, ts: Date.now() }
      setMessages([...nextMsgs, aiMsg])
      convRef.current.push({ role: 'assistant', content: aiContent })
      // Tentar extrair proposta de salvamento
      setProposal(tryExtractNote(aiContent))
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao falar com a IA')
    } finally {
      setBusy(false)
    }
  }

  async function saveProposal() {
    if (!proposal || !userId) return
    setSaving(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await adminApi.applyUserAnalysisNote(userId, {
        title: proposal.title,
        content: proposal.content,
        kind: proposal.kind,
        conversation: convRef.current,
      })
      setSuccess(`✅ Nota salva: "${data.note.title}" (${data.note.kind}).`)
      setProposal(null)
      onSaved?.()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar nota')
    } finally {
      setSaving(false)
    }
  }

  // Cor baseada no kind detectado
  const currentKindMeta = proposal ? KIND_LABEL[proposal.kind] : null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(6px)' }}
      onClick={(busy || saving) ? undefined : onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl flex flex-col"
        style={{
          background: '#0A0A0A',
          border: `2px solid rgba(168, 85, 247, 0.35)`,
          maxHeight: '88vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className="flex items-center justify-between p-4 border-b"
          style={{ borderColor: '#1E1E2E' }}
        >
          <div className="flex items-center gap-2">
            <Sparkles size={20} style={{ color: '#A855F7' }} />
            <h3 className="text-base font-bold text-ayria-text">
              Análise de {firstName} — IA
            </h3>
            <span
              className="text-[10px] px-2 py-0.5 rounded uppercase font-bold flex items-center gap-1"
              style={{ background: 'rgba(168,85,247,0.15)', color: '#A855F7' }}
            >
              <Lock size={10} /> contexto travado neste user
            </span>
          </div>
          <button
            onClick={onClose}
            disabled={busy || saving}
            className="text-ayria-muted hover:text-white disabled:opacity-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* Contexto atual */}
        <div className="px-4 py-2 text-[11px] text-ayria-muted border-b flex items-center gap-1.5" style={{ borderColor: '#1E1E2E' }}>
          <User size={12} className="flex-shrink-0" />
          <span>
            IA vê <strong className="text-ayria-text">apenas</strong> este user (perfil, sub-alma, últimas msgs, alertas, notas anteriores).
          </span>
        </div>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: '260px', maxHeight: 'calc(88vh - 320px)' }}>
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className="max-w-[85%] px-3 py-2 rounded-lg text-sm whitespace-pre-wrap"
                style={
                  m.role === 'user'
                    ? {
                        background: 'linear-gradient(135deg, #6366F1, #A855F7)',
                        color: '#fff',
                      }
                    : {
                        background: '#141420',
                        border: '1px solid rgba(168,85,247,0.25)',
                        color: '#E5E7EB',
                      }
                }
              >
                {m.content}
              </div>
            </div>
          ))}

          {/* Proposta de salvamento */}
          {proposal && currentKindMeta && (
            <div
              className="rounded-lg p-3 text-xs space-y-2"
              style={{
                background: `${currentKindMeta.color}10`,
                border: `1px solid ${currentKindMeta.color}55`,
              }}
            >
              <div className="font-semibold flex items-center gap-1.5" style={{ color: currentKindMeta.color }}>
                <span>{currentKindMeta.emoji}</span>
                <Save size={12} />
                <span>Nota detectada — {currentKindMeta.label}</span>
              </div>
              <div className="text-ayria-text font-bold text-sm">{proposal.title}</div>
              <div className="text-ayria-muted line-clamp-3 italic">
                {proposal.content.slice(0, 240)}{proposal.content.length > 240 ? '…' : ''}
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={saveProposal}
                  disabled={saving}
                  className="text-xs px-3 py-1.5 rounded-lg text-white font-bold flex items-center gap-1.5 disabled:opacity-40"
                  style={{
                    background: `linear-gradient(135deg, ${currentKindMeta.color}, ${currentKindMeta.color}dd)`,
                  }}
                >
                  {saving ? (
                    <>
                      <Loader2 size={12} className="animate-spin" />
                      Salvando...
                    </>
                  ) : (
                    <>
                      <Save size={12} />
                      Salvar como nota persistente
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {/* Busy */}
          {busy && (
            <div className="flex justify-start">
              <div
                className="px-3 py-2 rounded-lg text-sm flex items-center gap-2"
                style={{
                  background: '#141420',
                  border: '1px solid rgba(168,85,247,0.25)',
                  color: '#94A3B8',
                }}
              >
                <Loader2 size={14} className="animate-spin" />
                <span>IA analisando <strong style={{ color: '#A855F7' }}>{firstName}</strong>...</span>
              </div>
            </div>
          )}

          {/* Erro */}
          {error && (
            <div
              className="p-3 rounded-lg text-xs text-red-300 flex items-start gap-2"
              style={{ background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)' }}
            >
              <AlertTriangle size={14} className="flex-shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {/* Sucesso */}
          {success && (
            <div
              className="p-3 rounded-lg text-xs text-green-300 flex items-start gap-2"
              style={{ background: 'rgba(34,197,94,0.1)', border: '1px solid rgba(34,197,94,0.3)' }}
            >
              <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
              <span>{success}</span>
            </div>
          )}

          <div ref={endRef} />
        </div>

        {/* Input */}
        <div className="p-4 border-t" style={{ borderColor: '#1E1E2E' }}>
          <div className="flex items-end gap-2">
            <div className="flex-1">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault()
                    send()
                  }
                }}
                disabled={busy || saving}
                placeholder={`Pergunte sobre ${firstName}: "está em crise?", "resuma as últimas 10 msgs", "qual o nível de risco"...`}
                className="w-full px-3 py-2 rounded-lg text-sm resize-none focus:outline-none focus:ring-2 disabled:opacity-50"
                style={{
                  background: '#141420',
                  border: '1px solid #1E1E2E',
                  color: '#E5E7EB',
                  minHeight: '44px',
                  maxHeight: '100px',
                }}
              />
              <div className="text-[10px] text-ayria-muted mt-1">
                Enter envia · Shift+Enter quebra linha · sem custo p/ admin
              </div>
            </div>
            <button
              onClick={send}
              disabled={!input.trim() || busy || saving}
              className="px-4 py-2.5 rounded-lg text-sm font-bold text-white flex items-center gap-1.5 disabled:opacity-40 transition"
              style={{
                background:
                  input.trim() && !busy && !saving
                    ? 'linear-gradient(135deg, #A855F7, #6366F1)'
                    : '#1E1E2E',
              }}
            >
              {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
              Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}