/**
 * AYRIA - Prompt Chat Modal
 *
 * Popup de chat com contexto do MD selecionado.
 * O admin conversa comigo sobre o prompt atual — eu analiso, sugiro
 * mudanças, e ofereço versão nova. O botão "Salvar" aplica.
 *
 * Usado em: AlmaTab (cards de Módulos + Constituição) e aba Supervisão
 * (card do prompt crítico).
 */
import { useEffect, useRef, useState } from 'react'
import { MessageCircle, Send, X, Save, Loader2, Sparkles } from 'lucide-react'
import { adminApi } from '../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Props {
  open: boolean
  onClose: () => void
  /** key do prompt: 'constituicao_base', 'modulo_<short>', 'supervisor_seguranca_crise' */
  promptKey: string
  /** Label legível pra mostrar no header */
  promptLabel: string
  /** Quando salva uma nova versão — atualiza estado externo */
  onSaved?: (newContent: string) => void
  /** Conteúdo inicial (módulo novo em criação, sem banco/arquivo) */
  initialContext?: string
  /** 🆕 Quando o fluxo é criar módulo: salva E cria automaticamente (no fluxo de novo módulo) */
  onSaveAndCreate?: (newContent: string) => void
}

export function PromptChatModal({
  open,
  onClose,
  promptKey,
  promptLabel,
  onSaved,
  initialContext,
  onSaveAndCreate,
}: Props) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [proposedContent, setProposedContent] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) {
      setMessages([])
      setInput('')
      setError(null)
      setSuccessMsg(null)
      setProposedContent(null)
    }
  }, [open, promptKey])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages, loading])

  if (!open) return null

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = { role: 'user', content: text }
    const next = [...messages, userMsg]
    setMessages(next)
    setInput('')
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    setProposedContent(null)

    try {
      const { data } = await adminApi.promptChat({
        key: promptKey,
        user_message: text,
        history: messages,
        initial_context: initialContext || null,
      })
      const assistantMsg: Message = {
        role: 'assistant',
        content: data.assistant_response,
      }
      setMessages([...next, assistantMsg])

      // Detecta se a resposta propôs uma nova versão. Aceita 3 formatos:
      // 1) Bloco markdown com fence ```markdown ... ```
      // 2) Texto começando com "# MÓDULO:" (módulo completo)
      // 3) Texto com múltiplos ## headings + conteúdo substancial
      const assistantResp = data.assistant_response
      let proposedCandidate: string | null = null

      // 1) Bloco markdown
      const mdMatch = assistantResp.match(/```(?:markdown|md)?\s*\n([\s\S]*?)```/g)
      if (mdMatch && mdMatch.length > 0) {
        const largest = mdMatch.reduce((a, b) => (a.length > b.length ? a : b))
        const inner = largest.replace(/^```(?:markdown|md)?\s*\n/, '').replace(/```$/, '').trim()
        if (inner.length > 100) proposedCandidate = inner
      }

      // 2) Texto começando com # MÓDULO: (sem fence)
      if (!proposedCandidate) {
        const moduleHeader = assistantResp.match(/^(# MÓDULO:[\s\S]+)/m)
        if (moduleHeader && moduleHeader[1].length > 200) {
          // Pega do "# MÓDULO:" até o final (assumindo que é a versão proposta)
          const txt = moduleHeader[1].trim()
          // Evita pegar só o cabeçalho — exige pelo menos 1 seção ##
          if (txt.includes('\n##') || txt.includes('\n###')) {
            proposedCandidate = txt
          }
        }
      }

      if (proposedCandidate) {
        setProposedContent(proposedCandidate)
      }
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao conversar com IA')
    } finally {
      setLoading(false)
    }
  }

  const handleSaveProposed = async () => {
    if (!proposedContent || saving) return
    if (!confirm('Salvar a versão proposta? O arquivo atual vira .bak e o conteúdo novo entra no lugar.')) return
    setSaving(true)
    setError(null)
    setSuccessMsg(null)
    try {
      const { data } = await adminApi.promptChatSave({
        key: promptKey,
        new_content: proposedContent,
        reindex_rag: true,
      })
      setSuccessMsg(`✅ Salvo! Backup: ${data.backup?.split('/').pop() || '(sem backup anterior)'} · Reindex RAG: ${data.reindexed ? 'sim' : 'não'}`)
      setProposedContent(null)
      onSaved?.(proposedContent)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-3xl rounded-2xl flex flex-col"
        style={{
          background: '#0a0a0a',
          border: '1px solid #1E1E2E',
          maxHeight: '85vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* HEADER */}
        <div
          className="flex items-center gap-3 p-4 border-b"
          style={{ borderColor: '#1E1E2E' }}
        >
          <div
            className="p-2 rounded-lg"
            style={{ background: 'linear-gradient(135deg, rgba(99,102,241,0.2), rgba(168,85,247,0.2))' }}
          >
            <MessageCircle size={18} className="text-purple-300" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-semibold text-ayria-text">Chat sobre prompt</div>
            <div className="text-[10px] text-ayria-muted truncate">
              <code className="text-purple-300">{promptKey}</code> · {promptLabel}
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-ayria-muted hover:text-ayria-text hover:bg-ayria-admin/10"
          >
            <X size={18} />
          </button>
        </div>

        {/* MESSAGES */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3" style={{ minHeight: 300 }}>
          {messages.length === 0 && (
            <div className="text-center text-ayria-muted py-8 space-y-2">
              <Sparkles size={28} className="mx-auto text-purple-400" />
              <div className="text-sm">Comece a conversa sobre este prompt</div>
              <div className="text-xs text-ayria-muted/70 max-w-md mx-auto">
                Pergunte o que ele faz, peça análise crítica, sugira melhorias, ou peça uma versão nova completa.
                Quando eu propuser uma nova versão em bloco de código, o botão <b>Salvar versão proposta</b> aparece.
              </div>
              <div className="flex flex-wrap gap-2 justify-center pt-3 text-xs">
                {[
                  'Esse prompt tá bom? O que pode melhorar?',
                  'Tem algum erro ou inconsistência?',
                  'Me dá uma versão melhorada',
                  'Como esse prompt é carregado?',
                ].map((s) => (
                  <button
                    key={s}
                    onClick={() => setInput(s)}
                    className="px-3 py-1.5 rounded-lg border border-ayria-border text-ayria-muted hover:text-ayria-text hover:border-purple-500/30"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, idx) => {
            // Mostra botão de salvar DENTRO do último assistant message quando há proposed
            const isLastAssistant = m.role === 'assistant' && idx === messages.length - 1
            return (
              <div
                key={idx}
                className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-[85%] p-3 rounded-2xl text-sm whitespace-pre-wrap ${
                    m.role === 'user'
                      ? 'bg-purple-600/30 text-purple-100 border border-purple-500/30'
                      : 'bg-ayria-admin/10 text-ayria-text border border-ayria-admin/20'
                  }`}
                >
                  {m.content}
                  {/* 🆕 BOTÃO INLINE: só aparece se houver proposedContent detectado */}
                  {isLastAssistant && proposedContent && proposedContent.length > 0 && (
                    <div
                      className="mt-3 p-3 rounded-xl border-2 flex items-center justify-between gap-2"
                      style={{
                        background: 'linear-gradient(135deg, rgba(168,85,247,0.15), rgba(99,102,241,0.15))',
                        borderColor: 'rgba(168,85,247,0.5)',
                        boxShadow: '0 0 12px rgba(168,85,247,0.2)',
                      }}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-purple-200 flex items-center gap-1">
                          <Sparkles size={14} />
                          💡 Nova versão proposta ({proposedContent.length} chars)
                        </div>
                        <div className="text-[10px] text-ayria-muted mt-0.5">
                          Clique pra aplicar no prompt
                        </div>
                      </div>
                      <div className="flex gap-1">
                        <button
                          onClick={() => setProposedContent(null)}
                          className="text-[10px] px-2 py-1 rounded text-ayria-muted hover:text-ayria-text"
                          title="Descartar proposta"
                        >
                          ✕
                        </button>
                        <button
                          onClick={handleSaveProposed}
                          disabled={saving}
                          className="text-xs px-3 py-1.5 rounded-lg font-semibold text-white disabled:opacity-50 flex items-center gap-1 whitespace-nowrap"
                          style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
                        >
                          {saving ? <Loader2 size={12} className="animate-spin" /> : <Save size={12} />}
                          {saving ? 'Salvando...' : 'Salvar'}
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )
          })}

          {loading && (
            <div className="flex justify-start">
              <div className="bg-ayria-admin/10 border border-ayria-admin/20 p-3 rounded-2xl text-sm text-ayria-muted flex items-center gap-2">
                <Loader2 size={14} className="animate-spin" />
                Analisando prompt...
              </div>
            </div>
          )}

          {error && (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-sm text-red-300">
              {error}
            </div>
          )}

          {successMsg && (
            <div className="p-3 rounded-lg bg-green-500/10 border border-green-500/30 text-sm text-green-300">
              {successMsg}
            </div>
          )}
        </div>

        {/* INPUT */}
        <div className="p-3 border-t" style={{ borderColor: '#1E1E2E' }}>
          <div className="flex gap-2 items-end">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Pergunte sobre o prompt ou peça uma versão nova..."
              className="flex-1 px-3 py-2 rounded-lg bg-ayria-bg text-ayria-text text-sm resize-none focus:outline-none focus:border-purple-500/40"
              style={{ border: '1px solid #1E1E2E', maxHeight: 100 }}
              rows={2}
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 rounded-lg text-white font-semibold disabled:opacity-40 flex items-center gap-2"
              style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
            >
              <Send size={14} />
              Enviar
            </button>
          </div>
          <div className="text-[10px] text-ayria-muted mt-1.5">
            Enter envia · Shift+Enter quebra linha
          </div>
        </div>
      </div>
    </div>
  )
}