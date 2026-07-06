/**
 * AYRIA - Message Debug Modal (Admin)
 *
 * Mostra ao admin (modo observador) TUDO que a IA viu naquela resposta:
 * 1. System prompt completo
 * 2. Mensagens enviadas (system + history + user)
 * 3. Contexto interpretado (perfil, RAG, memórias — preview)
 * 4. Tokens input/output
 * 5. Sinais do supervisor
 *
 * Objetivo: permitir que o admin audite o que a Ayria "pensou" e edite o prompt
 * no menu ALMA se necessário.
 */
import { useState } from 'react'
import { X, Cpu, Eye, FileText, Database, Brain, Activity, ChevronDown, ChevronRight, Copy, Check, Sparkles } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  ai_model?: string | null
  tokens_used?: number | null
  metadata?: any
  created_at: string
}

export function MessageDebugModal({ message, onClose }: { message: Message; onClose: () => void }) {
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    interpreted: true,
    system_prompt: true,
    messages_sent: true,
    supervisor: false,
  })
  const [copiedField, setCopiedField] = useState<string | null>(null)

  const toggle = (k: string) => setExpandedSections((s) => ({ ...s, [k]: !s[k] }))

  const copy = (text: string, field: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopiedField(field)
      setTimeout(() => setCopiedField(null), 2000)
    })
  }

  if (message.role !== 'assistant') {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center px-4"
        style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(6px)' }}
        onClick={onClose}
      >
        <div
          className="rounded-2xl p-6 max-w-md"
          style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="text-ayria-text text-center">
            <div className="text-2xl mb-2">👤</div>
            <div>Esta é uma mensagem do usuário — não passa pela IA.</div>
            <button
              onClick={onClose}
              className="mt-4 px-4 py-2 rounded-lg text-sm"
              style={{ background: '#1E1E2E' }}
            >
              Fechar
            </button>
          </div>
        </div>
      </div>
    )
  }

  const meta = message.metadata || {}
  const systemPrompt = meta.system_prompt_used || '⚠️ Não salvo nesta mensagem (versão antiga do backend)'
  const messagesSent = meta.messages_sent_to_ai || []
  const interpreted = meta.interpreted_context || {}
  const tokensIn = meta.tokens_input_estimated
  const tokensOut = meta.tokens_output || message.tokens_used
  const model = meta.model_used || message.ai_model

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center px-4 py-8 overflow-y-auto"
      style={{ background: 'rgba(0,0,0,0.85)', backdropFilter: 'blur(6px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-4xl rounded-2xl my-auto"
        style={{ background: '#0A0A0A', border: '1px solid #1E1E2E' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-4 border-b flex items-center justify-between" style={{ borderColor: '#1E1E2E' }}>
          <div className="flex items-center gap-3">
            <div
              className="w-10 h-10 rounded-full flex items-center justify-center"
              style={{ background: 'linear-gradient(135deg, #A855F7, #6366F1)' }}
            >
              <Eye size={18} className="text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold gradient-text">Contexto da resposta da Ayria</h2>
              <div className="text-xs text-ayria-muted">
                {new Date(message.created_at).toLocaleString('pt-BR')}
              </div>
            </div>
          </div>
          <button onClick={onClose} className="text-ayria-muted hover:text-white p-2">
            <X size={20} />
          </button>
        </div>

        <div className="px-6 py-4 max-h-[75vh] overflow-y-auto space-y-4">
          {/* Quick stats */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <StatBox icon={<Cpu size={14} />} label="Modelo" value={model || '—'} color="#A855F7" />
            <StatBox
              icon={<FileText size={14} />}
              label="Tokens (input est.)"
              value={tokensIn != null ? tokensIn.toLocaleString('pt-BR') : '—'}
              color="#6366F1"
            />
            <StatBox
              icon={<FileText size={14} />}
              label="Tokens (output)"
              value={tokensOut != null ? tokensOut.toLocaleString('pt-BR') : '—'}
              color="#10B981"
            />
            <StatBox
              icon={<Activity size={14} />}
              label="Supervisor"
              value={interpreted.supervisor_quick_level || '—'}
              color={
                interpreted.supervisor_quick_level === 'URGENCIA'
                  ? '#EF4444'
                  : interpreted.supervisor_quick_level === 'ATENCAO'
                    ? '#F59E0B'
                    : '#10B981'
              }
            />
          </div>

          {/* Arquitetura modular */}
          {meta.prompt_architecture === 'modular_v2' && (
            <div
              className="p-4 rounded-xl"
              style={{ background: 'linear-gradient(135deg, rgba(168,85,247,0.08), rgba(99,102,241,0.08))', border: '1px solid rgba(168, 85, 247, 0.3)' }}
            >
              <div className="flex items-center gap-2 mb-2">
                <Sparkles size={16} style={{ color: '#A855F7' }} />
                <span className="text-sm font-bold text-ayria-text">Arquitetura Modular v2</span>
              </div>
              <div className="text-xs text-ayria-muted mb-2">
                Prompt montado dinamicamente — só os módulos necessários foram carregados.
              </div>
              {meta.selected_modules && meta.selected_modules.length > 0 ? (
                <div className="flex flex-wrap gap-1.5">
                  {meta.selected_modules.map((mod: string) => (
                    <span
                      key={mod}
                      className="text-xs px-2 py-0.5 rounded font-mono"
                      style={{ background: '#A855F7', color: '#FFFFFF' }}
                      title={meta.prompt_reason?.[mod] || 'módulo carregado'}
                    >
                      {mod}
                    </span>
                  ))}
                </div>
              ) : (
                <div className="text-xs text-ayria-muted italic">Apenas a constituição base foi carregada (módulos desnecessários)</div>
              )}
              {meta.prompt_reason && (
                <details className="mt-2 text-xs">
                  <summary className="cursor-pointer text-ayria-muted hover:text-ayria-text">Por que esses módulos?</summary>
                  <div className="mt-2 space-y-1">
                    {Object.entries(meta.prompt_reason).map(([k, v]: [string, any]) => (
                      <div key={k} className="text-ayria-muted">
                        <span className="font-mono px-1 rounded" style={{ background: '#1E1E2E' }}>{k}</span>: {v}
                      </div>
                    ))}
                  </div>
                </details>
              )}
            </div>
          )}

          {/* Interpreted Context (resumo do que viu) */}
          <Section
            title="🧠 O que a Ayria interpretou (resumo)"
            icon={<Brain size={16} />}
            expanded={expandedSections.interpreted}
            onToggle={() => toggle('interpreted')}
          >
            <div className="space-y-3">
              {interpreted.user_question && (
                <Field
                  label="Pergunta do usuário"
                  value={interpreted.user_question}
                  mono
                  onCopy={() => copy(interpreted.user_question, 'q')}
                  copied={copiedField === 'q'}
                />
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                <BoolField
                  label="Perfil do user"
                  used={interpreted.profile_used}
                  preview={interpreted.profile_preview}
                />
                <BoolField
                  label="RAG (conhecimento)"
                  used={interpreted.rag_used}
                  preview={interpreted.rag_preview}
                />
              </div>

              <div className="grid grid-cols-3 gap-3 text-xs">
                <SmallStat label="Histórico" value={`${interpreted.history_messages_count || 0} msgs`} />
                <SmallStat label="Memórias" value={`${interpreted.memories_count || 0} fatos`} />
                <SmallStat label="Pendentes" value={`${interpreted.pending_questions_count || 0} perguntas`} />
              </div>

              {interpreted.memories_preview && interpreted.memories_count > 0 && (
                <details className="text-xs">
                  <summary className="cursor-pointer text-ayria-muted hover:text-ayria-text py-1">
                    📝 Preview das memórias injetadas
                  </summary>
                  <pre
                    className="mt-2 p-3 rounded-lg overflow-x-auto whitespace-pre-wrap text-xs"
                    style={{ background: '#050505', border: '1px solid #1E1E2E' }}
                  >
                    {interpreted.memories_preview}
                  </pre>
                </details>
              )}
            </div>
          </Section>

          {/* System Prompt completo */}
          <Section
            title="📜 System Prompt enviado pra IA"
            icon={<FileText size={16} />}
            expanded={expandedSections.system_prompt}
            onToggle={() => toggle('system_prompt')}
            onCopy={() => copy(systemPrompt, 'sp')}
            copied={copiedField === 'sp'}
            copyLabel="Copiar prompt completo"
          >
            <pre
              className="p-4 rounded-lg overflow-x-auto whitespace-pre-wrap text-xs leading-relaxed"
              style={{
                background: '#050505',
                border: '1px solid #1E1E2E',
                color: '#A78BFA',
                fontFamily: 'ui-monospace, monospace',
                maxHeight: '400px',
              }}
            >
              {systemPrompt}
            </pre>
            <div className="text-xs text-ayria-muted mt-2">
              💡 <strong>Dica:</strong> pra editar isso, vá em <strong>Admin → aba ALMA</strong>. A mudança vale a partir da próxima mensagem.
            </div>
          </Section>

          {/* Messages sent to AI */}
          {messagesSent.length > 0 && (
            <Section
              title={`💬 Mensagens enviadas pra IA (${messagesSent.length})`}
              icon={<Database size={16} />}
              expanded={expandedSections.messages_sent}
              onToggle={() => toggle('messages_sent')}
            >
              <div className="space-y-2">
                {messagesSent.map((m: any, i: number) => (
                  <div
                    key={i}
                    className="p-3 rounded-lg"
                    style={{
                      background: m.role === 'system' ? 'rgba(168, 85, 247, 0.08)' : m.role === 'user' ? 'rgba(99, 102, 241, 0.08)' : '#050505',
                      border: `1px solid ${m.role === 'system' ? 'rgba(168, 85, 247, 0.3)' : m.role === 'user' ? 'rgba(99, 102, 241, 0.3)' : '#1E1E2E'}`,
                    }}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span
                        className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded"
                        style={{
                          background:
                            m.role === 'system' ? '#A855F7' : m.role === 'user' ? '#6366F1' : '#10B981',
                          color: '#FFFFFF',
                        }}
                      >
                        {m.role === 'system' ? '⚙️ system' : m.role === 'user' ? '👤 user' : '🤖 assistant'}
                      </span>
                      <span className="text-xs text-ayria-muted">
                        {(m.content || '').length} chars
                      </span>
                    </div>
                    <pre
                      className="text-xs whitespace-pre-wrap break-words overflow-x-auto"
                      style={{
                        color: '#E5E7EB',
                        fontFamily: 'ui-monospace, monospace',
                        maxHeight: '200px',
                        overflowY: 'auto',
                      }}
                    >
                      {m.role === 'system'
                        ? (m.content || '').substring(0, 500) + ((m.content || '').length > 500 ? '\n\n... [truncado — ver seção "System Prompt" acima pra ver completo]' : '')
                        : m.content}
                    </pre>
                  </div>
                ))}
              </div>
            </Section>
          )}

          {/* Supervisor signals */}
          {(interpreted.supervisor_quick_level || meta.supervisor_pre_flag) && (
            <Section
              title="🚦 Análise do Supervisor (risco)"
              icon={<Activity size={16} />}
              expanded={expandedSections.supervisor}
              onToggle={() => toggle('supervisor')}
            >
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-ayria-muted">Nível:</span>
                  <span
                    className="px-2 py-0.5 rounded text-xs font-bold"
                    style={{
                      background:
                        interpreted.supervisor_quick_level === 'URGENCIA'
                          ? 'rgba(239, 68, 68, 0.2)'
                          : interpreted.supervisor_quick_level === 'ATENCAO'
                            ? 'rgba(245, 158, 11, 0.2)'
                            : 'rgba(16, 185, 129, 0.2)',
                      color:
                        interpreted.supervisor_quick_level === 'URGENCIA'
                          ? '#EF4444'
                          : interpreted.supervisor_quick_level === 'ATENCAO'
                            ? '#F59E0B'
                            : '#10B981',
                    }}
                  >
                    {interpreted.supervisor_quick_level || 'NORMAL'}
                  </span>
                  <span className="text-ayria-muted text-xs">
                    (score: {interpreted.supervisor_quick_score?.toFixed(3) || '0.000'})
                  </span>
                </div>
              </div>
            </Section>
          )}

          {/* Thinking (se houver) */}
          {meta.thinking && (
            <details className="rounded-xl overflow-hidden" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
              <summary className="px-4 py-3 cursor-pointer text-sm font-semibold text-ayria-text hover:bg-[#1a1a1a] flex items-center justify-between">
                <span>🧩 Thinking (raciocínio vazado capturado)</span>
                <ChevronRight size={14} className="text-ayria-muted" />
              </summary>
              <pre
                className="px-4 pb-4 text-xs whitespace-pre-wrap"
                style={{ color: '#94A3B8', fontFamily: 'ui-monospace, monospace' }}
              >
                {meta.thinking}
              </pre>
            </details>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t flex items-center justify-between" style={{ borderColor: '#1E1E2E' }}>
          <div className="text-xs text-ayria-muted">
            ID da msg: <code className="px-1.5 py-0.5 rounded" style={{ background: '#1E1E2E' }}>{message.id.slice(0, 8)}...</code>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-sm text-ayria-text"
            style={{ background: '#1E1E2E' }}
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  )
}

// === Sub-componentes auxiliares ===
function Section({
  title,
  icon,
  expanded,
  onToggle,
  onCopy,
  copied,
  copyLabel,
  children,
}: {
  title: string
  icon: React.ReactNode
  expanded: boolean
  onToggle: () => void
  onCopy?: () => void
  copied?: boolean
  copyLabel?: string
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl overflow-hidden" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      <div className="px-4 py-3 flex items-center justify-between hover:bg-[#1a1a1a] transition-colors">
        <button onClick={onToggle} className="flex items-center gap-2 text-ayria-text font-semibold flex-1 text-left text-sm">
          {icon}
          {title}
          {expanded ? <ChevronDown size={14} className="text-ayria-muted ml-2" /> : <ChevronRight size={14} className="text-ayria-muted ml-2" />}
        </button>
        {onCopy && (
          <button
            onClick={onCopy}
            className="text-xs px-2.5 py-1 rounded flex items-center gap-1.5"
            style={{ background: '#1E1E2E', color: copied ? '#10B981' : '#A855F7' }}
            title={copyLabel}
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            {copied ? 'Copiado!' : copyLabel || 'Copiar'}
          </button>
        )}
      </div>
      {expanded && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  )
}

function StatBox({ icon, label, value, color }: { icon: React.ReactNode; label: string; value: string; color: string }) {
  return (
    <div className="p-3 rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      <div className="flex items-center gap-1.5 text-xs text-ayria-muted mb-1">
        <span style={{ color }}>{icon}</span>
        <span>{label}</span>
      </div>
      <div className="text-sm font-bold" style={{ color }}>
        {value}
      </div>
    </div>
  )
}

function SmallStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2 rounded text-center" style={{ background: '#050505', border: '1px solid #1E1E2E' }}>
      <div className="text-xs text-ayria-muted">{label}</div>
      <div className="text-sm font-bold text-ayria-text">{value}</div>
    </div>
  )
}

function Field({ label, value, mono, onCopy, copied }: { label: string; value: string; mono?: boolean; onCopy?: () => void; copied?: boolean }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <div className="text-xs text-ayria-muted">{label}</div>
        {onCopy && (
          <button onClick={onCopy} className="text-xs px-2 py-0.5 rounded flex items-center gap-1" style={{ background: '#1E1E2E', color: copied ? '#10B981' : '#A855F7' }}>
            {copied ? <Check size={10} /> : <Copy size={10} />}
            {copied ? 'Copiado' : 'Copiar'}
          </button>
        )}
      </div>
      <div
        className="p-2 rounded text-sm"
        style={{
          background: '#050505',
          border: '1px solid #1E1E2E',
          fontFamily: mono ? 'ui-monospace, monospace' : 'inherit',
          color: '#E5E7EB',
          wordBreak: 'break-word',
        }}
      >
        {value}
      </div>
    </div>
  )
}

function BoolField({ label, used, preview }: { label: string; used: boolean; preview?: string }) {
  return (
    <div
      className="p-3 rounded-lg"
      style={{
        background: used ? 'rgba(16, 185, 129, 0.08)' : 'rgba(148, 163, 184, 0.05)',
        border: `1px solid ${used ? 'rgba(16, 185, 129, 0.3)' : '#1E1E2E'}`,
      }}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-semibold text-ayria-text">{label}</span>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded font-bold"
          style={{
            background: used ? '#10B981' : '#64748B',
            color: '#FFFFFF',
          }}
        >
          {used ? '✓ injetado' : 'vazio'}
        </span>
      </div>
      {used && preview && (
        <div className="text-xs text-ayria-muted mt-1 line-clamp-3" title={preview}>
          {preview}
        </div>
      )}
    </div>
  )
}