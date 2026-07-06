import { useState } from 'react'
import { adminApi } from '../lib/api'
import {
  X, ArrowRight, ArrowLeft, MessageCircle, Sparkles,
  AlertCircle, CheckCircle2, Loader2, FileText,
} from 'lucide-react'
import { PromptChatModal } from './PromptChatModal'

interface CreateModuleModalProps {
  open: boolean
  onClose: () => void
  onCreated: (key: string) => void
}

/**
 * Modal de criação de módulo novo. 2 passos:
 *   1. Nome (snake_case)
 *   2. Conteúdo (com Chat com IA opcional + textarea)
 *
 * Estado de "open":
 *   - false: ninguém renderiza nada (early-return)
 *   - true: overlay + popup centralizado
 *
 * Após criar: faz POST /update-prompt-system + POST /rag/index → onCreated(key).
 */
export function CreateModuleModal({ open, onClose, onCreated }: CreateModuleModalProps) {
  const [step, setStep] = useState<'name' | 'content'>('name')
  const [key, setKey] = useState('')
  const [content, setContent] = useState('')
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [chatOpen, setChatOpen] = useState(false)

  if (!open) return null

  const reset = () => {
    setStep('name')
    setKey('')
    setContent('')
    setError(null)
    setSuccess(null)
    setChatOpen(false)
  }

  const closeAndReset = () => {
    onClose()
    setTimeout(reset, 200)  // esperar animação de saída
  }

  const cleanKeyNow = key.trim().toLowerCase().replace(/[^a-z0-9_]/g, '')

  const submitCreate = async (contentToSave: string) => {
    setError(null)
    setSuccess(null)

    const cleanKey = key.trim().toLowerCase().replace(/[^a-z0-9_]/g, '')
    if (!cleanKey) {
      setError('Chave inválida.')
      return
    }
    if (!contentToSave.trim() || contentToSave.trim().length < 100) {
      setError('Conteúdo muito curto (mínimo 100 chars).')
      return
    }
    setWorking(true)
    try {
      await adminApi.updatePromptSystem({
        key: `modulo_${cleanKey}`,
        content: contentToSave.trim(),
        description: 'criado pela aba ALMA com ajuda da IA',
      })
      try {
        await adminApi.indexPromptsRag({ source: `modulo_${cleanKey}` })
      } catch (e) {
        console.warn('Indexação RAG falhou:', e)
      }
      setSuccess(`✅ Módulo "${cleanKey}" criado, salvo e indexado no RAG.`)
      setTimeout(() => {
        onCreated(cleanKey)
        closeAndReset()
      }, 1000)
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao criar módulo')
    } finally {
      setWorking(false)
    }
  }

  const handleChatSave = (newContent: string) => {
    setContent(newContent)
    setSuccess('✅ Conteúdo atualizado pelo chat. Clique "Criar + Indexar" pra finalizar.')
    setChatOpen(false)
  }

  const handleChatAutoCreate = (newContent: string) => {
    setContent(newContent)
    setChatOpen(false)
    // auto-cria + indexa
    setTimeout(() => submitCreate(newContent), 100)
  }

  // ════════════════════════════════════════════════════
  //  Render do Modal (overlay + card centralizado)
  // ════════════════════════════════════════════════════
  return (
    <>
      {/* OVERLAY */}
      <div
        className="fixed inset-0 z-40 flex items-center justify-center p-4"
        style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
        onClick={closeAndReset}
      >
        {/* CARD */}
        <div
          className="w-full max-w-2xl max-h-[90vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden"
          style={{
            background: '#0a0a0a',
            border: '1px solid rgba(168,85,247,0.4)',
            boxShadow: '0 0 40px rgba(168,85,247,0.2)',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* HEADER */}
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: '#1E1E2E' }}
          >
            <div className="flex items-center gap-2">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center"
                style={{
                  background: 'linear-gradient(135deg, #A855F7, #6366F1)',
                }}
              >
                <Sparkles size={14} className="text-white" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-ayria-text">
                  Criar novo módulo
                </h3>
                <div className="text-[10px] text-ayria-muted">
                  Passo {step === 'name' ? '1' : '2'} de 2 ·{' '}
                  <span style={{ color: '#A855F7' }}>{cleanKeyNow || '(sem nome)'}</span>
                </div>
              </div>
            </div>
            <button
              onClick={closeAndReset}
              className="p-1.5 rounded-lg hover:bg-white/5 text-ayria-muted hover:text-ayria-text"
              title="Fechar"
            >
              <X size={16} />
            </button>
          </div>

          {/* STEP INDICATOR (passos) */}
          <div className="flex gap-1 px-5 pt-3">
            <div
              className="flex-1 h-1 rounded-full"
              style={{
                background: step === 'name' ? '#A855F7' : '#6366F1',
                transition: 'all .3s',
              }}
            />
            <div
              className="flex-1 h-1 rounded-full"
              style={{
                background: step === 'content' ? '#A855F7' : '#1E1E2E',
                transition: 'all .3s',
              }}
            />
          </div>

          {/* BODY */}
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {step === 'name' && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-ayria-text mb-2">
                    Como quer chamar o módulo?
                  </label>
                  <input
                    type="text"
                    value={key}
                    onChange={(e) => setKey(e.target.value)}
                    placeholder="tarot, ikigai, ansiedade_social..."
                    className="w-full px-3 py-3 rounded-lg text-base text-ayria-text outline-none font-mono"
                    style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                    autoFocus
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && cleanKeyNow) {
                        setError(null)
                        setStep('content')
                      }
                    }}
                  />
                  <div className="text-[10px] text-ayria-muted mt-1.5 flex items-center justify-between">
                    <span>Será salvo como <code>modulo_{key || '...'}</code></span>
                    <span>{cleanKeyNow.length} caracteres válidos</span>
                  </div>
                </div>

                <div
                  className="p-3 rounded-xl flex gap-2 items-start"
                  style={{ background: 'rgba(168,85,247,0.05)', border: '1px solid rgba(168,85,247,0.2)' }}
                >
                  <Sparkles size={14} className="text-purple-400 mt-0.5 flex-shrink-0" />
                  <div className="text-xs text-ayria-muted">
                    <strong className="text-purple-300">No passo 2</strong> você pode usar o{' '}
                    <strong>Chat com IA</strong> pra construir o conteúdo junto comigo.
                    Eu mostro onde pode duplicar com outros módulos antes de propor algo,
                    e você só clica <strong>Salvar</strong> no final.
                  </div>
                </div>

                {error && (
                  <div
                    className="p-3 rounded-lg flex items-start gap-2 text-xs"
                    style={{ background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.3)' }}
                  >
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    {error}
                  </div>
                )}
              </>
            )}

            {step === 'content' && (
              <>
                <div className="flex gap-2">
                  <button
                    onClick={() => setChatOpen(true)}
                    className="flex-1 px-3 py-2.5 rounded-lg text-xs font-semibold flex items-center justify-center gap-2 transition-opacity hover:opacity-80"
                    style={{
                      background: 'linear-gradient(135deg, rgba(99,102,241,0.25), rgba(168,85,247,0.25))',
                      color: '#C084FC',
                      border: '1px solid rgba(168,85,247,0.4)',
                    }}
                  >
                    <MessageCircle size={14} />
                    {content.length > 0
                      ? `Editar com IA (${content.length} chars já)`
                      : '🪄 Chat com IA (construir do zero)'}
                  </button>
                  <button
                    onClick={() => setStep('name')}
                    className="px-3 py-2.5 rounded-lg text-xs font-medium flex items-center gap-1"
                    style={{ background: '#1E1E2E', color: '#94A3B8', border: '1px solid #2A2A3A' }}
                  >
                    <ArrowLeft size={14} /> Voltar
                  </button>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-ayria-text mb-2 flex items-center gap-1">
                    <FileText size={12} />
                    Conteúdo do prompt (markdown)
                  </label>
                  <textarea
                    value={content}
                    onChange={(e) => setContent(e.target.value)}
                    rows={14}
                    placeholder={`# MÓDULO: ${key.toUpperCase()}\n\nEste módulo orienta AYRIA a ...\n\n## OBJETIVO\n- ...\n\n## QUANDO ATIVAR\n- ...\n\n## REGRAS\n- ...\n\n## REFERÊNCIAS CRUZADAS\n- ...`}
                    className="w-full px-3 py-2.5 rounded-lg text-sm text-ayria-text outline-none font-mono"
                    style={{
                      background: '#050505',
                      border: '1px solid #1E1E2E',
                      lineHeight: '1.6',
                      resize: 'vertical',
                      minHeight: 240,
                    }}
                  />
                  <div className="flex justify-between text-[10px] text-ayria-muted mt-1.5">
                    <span>
                      <strong style={{ color: content.length >= 100 ? '#4ADE80' : '#94A3B8' }}>
                        {content.length} chars
                      </strong>{' '}
                      · ~{Math.ceil(content.length / 4)} tokens
                    </span>
                    <span>mínimo 100 chars para salvar</span>
                  </div>
                </div>

                {error && (
                  <div
                    className="p-3 rounded-lg flex items-start gap-2 text-xs"
                    style={{ background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', border: '1px solid rgba(239,68,68,0.3)' }}
                  >
                    <AlertCircle size={14} className="flex-shrink-0 mt-0.5" />
                    {error}
                  </div>
                )}

                {success && (
                  <div
                    className="p-3 rounded-lg flex items-start gap-2 text-xs"
                    style={{ background: 'rgba(74,222,128,0.1)', color: '#86EFAC', border: '1px solid rgba(74,222,128,0.3)' }}
                  >
                    <CheckCircle2 size={14} className="flex-shrink-0 mt-0.5" />
                    {success}
                  </div>
                )}
              </>
            )}
          </div>

          {/* FOOTER */}
          <div
            className="flex items-center justify-end gap-2 px-5 py-3 border-t"
            style={{ borderColor: '#1E1E2E', background: 'rgba(0,0,0,0.3)' }}
          >
            {step === 'name' ? (
              <>
                <button
                  onClick={closeAndReset}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-ayria-muted hover:text-ayria-text"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => {
                    if (!cleanKeyNow) {
                      setError('Chave inválida.')
                      return
                    }
                    setError(null)
                    setStep('content')
                  }}
                  disabled={!cleanKeyNow}
                  className="px-5 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50 flex items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
                >
                  Próximo <ArrowRight size={14} />
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={closeAndReset}
                  className="px-4 py-2 rounded-lg text-xs font-medium text-ayria-muted hover:text-ayria-text"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => submitCreate(content)}
                  disabled={working || content.length < 100}
                  className="px-5 py-2 rounded-lg text-sm font-semibold text-white disabled:opacity-50 flex items-center gap-2"
                  style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
                >
                  {working ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
                  {working ? 'Criando...' : 'Criar + Indexar no RAG'}
                </button>
              </>
            )}
          </div>
        </div>
      </div>

      {/* MODAL DE CHAT (interno, abre em camada acima) */}
      {chatOpen && (
        <PromptChatModal
          open={chatOpen}
          onClose={() => setChatOpen(false)}
          promptKey={`modulo_${key}_novo`}
          promptLabel={`Módulo NOVO: ${key}`}
          initialContext={content || `# MÓDULO: ${key.toUpperCase()}\n\n(Módulo em criação — defina o objetivo e estrutura)`}
          onSaved={handleChatSave}
          onSaveAndCreate={handleChatAutoCreate}
        />
      )}
    </>
  )
}
