/**
 * AYRIA - Keyword Block Chat Modal
 *
 * 🆕 08/07/2026: modal de chat que fica TRANCADO numa categoria de keywords.
 *  - Abre a partir do botão "💬 Editar com IA" no `SupervisorKeywordsViewer`
 *  - Backend injeta system prompt com contexto EXCLUSIVO desta categoria
 *  - Chat com IA sugerindo keywords (sempre em JSON estruturado)
 *  - Botão "Aplicar" pega o último bloco JSON da resposta e chama /apply
 *
 * Não é o `KeywordsEditorModal` (que edita o MD inteiro como texto).
 */

import { useEffect, useRef, useState } from 'react'
import { X, Send, Loader2, Sparkles, CheckCircle2, AlertTriangle, MessageSquare, Plus, Minus, Hash } from 'lucide-react'
import { adminApi } from '../lib/api'

interface Props {
  open: boolean
  category: string | null
  categoryLabel: string
  categoryColor: string
  currentKeywords: string[]
  onClose: () => void
  onApplied?: () => void
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  ts: number
}

interface ParsedProposal {
  add: string[]
  remove: string[]
  explanation?: string
}

const GREETING = (label: string) =>
  `Olá! Sou seu assistente de curadoria. Posso sugerir novas keywords, ajudar a remover redundantes, ou opinar sobre a categoria atual. Estamos exclusivamente trabalhando em **${label}**.`

function tryExtractProposal(text: string): ParsedProposal | null {
  // Tenta encontrar um JSON { "add": [...], "remove": [...], "explicacao": "..." } na resposta.
  // Aceita cópias com/sem ```json ... ``` wrapper.
  const clean = text.replace(/```json\s*/gi, '').replace(/```/g, '').trim()
  // 1) match do objeto {...} mais externo
  const start = clean.indexOf('{')
  const end = clean.lastIndexOf('}')
  if (start === -1 || end === -1 || end < start) return null
  const jsonStr = clean.substring(start, end + 1)
  try {
    const data = JSON.parse(jsonStr)
    if (Array.isArray(data.add) || Array.isArray(data.remove)) {
      return {
        add: (data.add || []).filter((x: any) => typeof x === 'string').map((s: string) => s.toLowerCase().trim()),
        remove: (data.remove || []).filter((x: any) => typeof x === 'string').map((s: string) => s.toLowerCase().trim()),
        explanation: typeof data.explicacao === 'string' ? data.explicacao : undefined,
      }
    }
  } catch {
    /* ignore */
  }
  return null
}

export function KeywordBlockChatModal({
  open,
  category,
  categoryLabel,
  categoryColor,
  currentKeywords,
  onClose,
  onApplied,
}: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [applying, setApplying] = useState(false)
  const [proposal, setProposal] = useState<ParsedProposal | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  // Resetar quando abre
  useEffect(() => {
    if (open && category) {
      setMessages([{ role: 'assistant', content: GREETING(categoryLabel), ts: Date.now() }])
      setInput('')
      setError(null)
      setSuccess(null)
      setProposal(null)
    }
  }, [open, category, categoryLabel])

  // ESC fecha
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open && !busy && !applying) onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose, busy, applying])

  // auto-scroll
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: 'end' })
  }, [messages, busy])

  if (!open || !category) return null

  async function send() {
    if (!input.trim() || busy || !category) return
    const userMsg: ChatMessage = { role: 'user', content: input.trim(), ts: Date.now() }
    const nextMsgs = [...messages, userMsg]
    setMessages(nextMsgs)
    setInput('')
    setBusy(true)
    setError(null)
    setSuccess(null)
    setProposal(null)
    try {
      const { data } = await adminApi.chatKeywordBlock(category, nextMsgs)
      const aiMsg: ChatMessage = {
        role: 'assistant',
        content: data?.message?.content || '(sem resposta da IA)',
        ts: Date.now(),
      }
      setMessages([...nextMsgs, aiMsg])
      // Tentar extrair proposta
      const parsed = tryExtractProposal(aiMsg.content)
      setProposal(parsed)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao falar com a IA')
    } finally {
      setBusy(false)
    }
  }

  async function applyProposal() {
    if (!proposal || !category) return
    setApplying(true)
    setError(null)
    setSuccess(null)
    try {
      const { data } = await adminApi.applyKeywordBlock(category, {
        keywords_to_add: proposal.add,
        keywords_to_remove: proposal.remove,
      })
      setSuccess(
        `✅ Aplicado em ${category}: +${data.added.length} adicionadas, -${data.removed.length} removidas. Total agora: ${data.keywords_after}.`
      )
      setProposal(null)
      // Atualizar contagem no parent
      onApplied?.()
      // Limpar cache do viewer (reload)
      setTimeout(() => {
        // Scrolla pro fim pra user ver o success
        endRef.current?.scrollIntoView({ block: 'end' })
      }, 100)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao aplicar')
    } finally {
      setApplying(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center px-4"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(6px)' }}
      onClick={(busy || applying) ? undefined : onClose}
    >
      <div
        className="w-full max-w-2xl rounded-2xl flex flex-col"
        style={{
          background: '#0A0A0A',
          border: `2px solid ${categoryColor}55`,
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
            <Sparkles size={20} style={{ color: categoryColor }} />
            <h3 className="text-base font-bold text-ayria-text">
              Editar {categoryLabel.split('—')[0].trim()} com IA
            </h3>
            <span
              className="text-[10px] px-2 py-0.5 rounded uppercase font-bold"
              style={{ background: `${categoryColor}20`, color: categoryColor }}
            >
              🔒 contexto travado
            </span>
          </div>
          <button
            onClick={onClose}
            disabled={busy || applying}
            className="text-ayria-muted hover:text-white disabled:opacity-30"
          >
            <X size={20} />
          </button>
        </div>

        {/* Contexto atual */}
        <div className="px-4 py-2 text-[11px] text-ayria-muted border-b" style={{ borderColor: '#1E1E2E' }}>
          <span>
            <strong className="text-ayria-text">{currentKeywords.length}</strong> keywords atualmente. A IA só vê esta categoria.
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
                        background: 'linear-gradient(135deg, #f1c961, #da950b)',
                        color: '#fff',
                      }
                    : {
                        background: '#141420',
                        border: `1px solid ${categoryColor}30`,
                        color: '#E5E7EB',
                      }
                }
              >
                {m.content}
              </div>
            </div>
          ))}

          {/* Proposta (clica-aplicar) */}
          {proposal && (proposal.add.length > 0 || proposal.remove.length > 0) && (
            <div
              className="rounded-lg p-3 text-xs space-y-2"
              style={{
                background: `${categoryColor}10`,
                border: `1px solid ${categoryColor}55`,
              }}
            >
              <div className="font-semibold flex items-center gap-1.5" style={{ color: categoryColor }}>
                <Hash size={12} />
                Proposta detectada:
              </div>
              {proposal.explanation && (
                <div className="text-ayria-muted italic">{proposal.explanation}</div>
              )}
              <div className="flex flex-wrap gap-2">
                {proposal.add.map((k, i) => (
                  <span
                    key={'a' + i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono"
                    style={{ background: 'rgba(34,197,94,0.15)', color: '#86EFAC', border: '1px solid rgba(34,197,94,0.4)' }}
                  >
                    <Plus size={10} /> {k}
                  </span>
                ))}
                {proposal.remove.map((k, i) => (
                  <span
                    key={'r' + i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded font-mono line-through"
                    style={{ background: 'rgba(239,68,68,0.15)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.4)' }}
                  >
                    <Minus size={10} /> {k}
                  </span>
                ))}
              </div>
              <button
                onClick={applyProposal}
                disabled={applying}
                className="mt-1 text-xs px-3 py-1.5 rounded-lg text-white font-bold flex items-center gap-1.5 disabled:opacity-40"
                style={{
                  background: `linear-gradient(135deg, ${categoryColor}, ${categoryColor}dd)`,
                  filter: 'brightness(0.9)',
                }}
              >
                {applying ? (
                  <>
                    <Loader2 size={12} className="animate-spin" />
                    Aplicando...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={12} />
                    Aplicar proposta
                  </>
                )}
              </button>
            </div>
          )}

          {/* Busy */}
          {busy && (
            <div className="flex justify-start">
              <div
                className="px-3 py-2 rounded-lg text-sm flex items-center gap-2"
                style={{
                  background: '#141420',
                  border: `1px solid ${categoryColor}30`,
                  color: '#94A3B8',
                }}
              >
                <Loader2 size={14} className="animate-spin" />
                <span>IA pensando em <strong style={{ color: categoryColor }}>{category}</strong>...</span>
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
                disabled={busy || applying}
                placeholder={`Peça: "adicione 5 termos sobre overdose", "remova redundantes", "liste as 5 piores"...`}
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
                Enter envia · Shift+Enter quebra linha · contexto: <span style={{ color: categoryColor }} className="font-bold">{category}</span>
              </div>
            </div>
            <button
              onClick={send}
              disabled={!input.trim() || busy || applying}
              className="px-4 py-2.5 rounded-lg text-sm font-bold text-white flex items-center gap-1.5 disabled:opacity-40 transition"
              style={{
                background:
                  input.trim() && !busy && !applying
                    ? `linear-gradient(135deg, ${categoryColor}, ${categoryColor}cc)`
                    : '#1E1E2E',
              }}
            >
              {busy ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <Send size={14} />
              )}
              Enviar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
