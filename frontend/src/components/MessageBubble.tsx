/**
 * AYRIA - Message Bubble
 *
 * Mostra APENAS o conteúdo da mensagem para usuários comuns.
 * Para ADMIN/SUPER_ADMIN, mostra também: modelo IA, tokens, e thinking
 * (raciocínio vazado pelo modelo) — info útil pra debug.
 *
 * Feature "Ver mais/menos":
 * - Mensagens longas (>= COLLAPSE_THRESHOLD_CHARS) começam truncadas
 * - Mostra o começo + indicador "..." + botão "Ver mais"
 * - Admin/SUPER_ADMIN sempre vê tudo expandido (sem truncar, sem botão)
 * - Truncamento é no último ESPAÇO antes do threshold (não corta palavra)
 */
import { useEffect, useRef, useState } from 'react'
import { Brain, ChevronDown, ChevronUp } from 'lucide-react'
import { useAuth } from '../store/auth'
import { LogoIcon } from './Logo'

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  tokens?: number
  thinking?: string | null
  /** Liga/desliga o colapso de mensagens longas. Default: true. */
  collapseEnabled?: boolean
  /** Mensagem da IA é uma pergunta pendente de onboarding (Sistema 2). */
  isPendingQuestion?: boolean
  /** Label do atributo pendente (ex: "Hora de nascimento"). */
  pendingAttrLabel?: string | null
  /** Timestamp ISO da mensagem (pra exibir dia/hora no rodapé do bubble). */
  timestamp?: string | null
}

// Threshold pra considerar uma mensagem "longa" e mostrar botão "Ver mais"
const COLLAPSE_THRESHOLD_CHARS = 400

/**
 * Formata timestamp pra exibir no rodapé do bubble.
 * - Hoje:           "Hoje DD/MM HH:MM"   (ex: "Hoje 01/07 14:32")
 * - Ontem:          "Ontem DD/MM HH:MM"  (ex: "Ontem 30/06 21:04")
 * - Mesmo ano:      "DD/MM HH:MM"        (ex: "28/06 09:15")
 * - Outro ano:      "DD/MM/AA HH:MM"     (ex: "31/12/25 23:58")
 *
 * SEMPRE mostra data + hora (depois do feedback do Rafael).
 */
function formatBubbleTimestamp(iso: string): string {
  const date = new Date(iso)
  if (isNaN(date.getTime())) return ''
  const now = new Date()
  const sameDay =
    date.getFullYear() === now.getFullYear() &&
    date.getMonth() === now.getMonth() &&
    date.getDate() === now.getDate()
  const yesterday = new Date(now)
  yesterday.setDate(now.getDate() - 1)
  const isYesterday =
    date.getFullYear() === yesterday.getFullYear() &&
    date.getMonth() === yesterday.getMonth() &&
    date.getDate() === yesterday.getDate()

  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  const time = `${hh}:${mm}`
  const dd = String(date.getDate()).padStart(2, '0')
  const mo = String(date.getMonth() + 1).padStart(2, '0')

  if (sameDay) return `Hoje ${dd}/${mo} ${time}`
  if (isYesterday) return `Ontem ${dd}/${mo} ${time}`
  if (date.getFullYear() === now.getFullYear()) {
    return `${dd}/${mo} ${time}`
  }
  const yy = String(date.getFullYear()).slice(-2)
  return `${dd}/${mo}/${yy} ${time}`
}

export function renderMarkdown(text: string): string {
  let rendered = text
    .replace(/### (.*)/g, '<h3>$1</h3>')
    .replace(/## (.*)/g, '<h2>$1</h2>')
    .replace(/# (.*)/g, '<h1>$1</h1>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/^> (.*)/gm, '<blockquote>$1</blockquote>')
    .replace(/^---$/gm, '<hr/>')
    .replace(/^- (.*)/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>')
    .replace(/\n/g, '<br/>')

  // Destaque especial: 'AYRIA' em MAGENTA VIBRANTE (cor do logo cyberpunk neon)
  rendered = rendered.replace(
    /\bAYRIA\b/g,
    '<span style="color: #EC4899; font-weight: 700; background: linear-gradient(135deg, #00FFFF, #EC4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-shadow: 0 0 12px rgba(236, 72, 153, 0.5);">AYRIA</span>'
  )

  return rendered
}

/**
 * Trunca texto no último ESPAÇO antes do limite.
 * Retorna { truncated, wasTruncated }.
 * - wasTruncated=false → texto cabe inteiro, sem truncar
 * - wasTruncated=true → texto foi cortado no último espaço + " ..."
 */
function truncateAtWord(text: string, limit: number): { truncated: string; wasTruncated: boolean } {
  if (text.length <= limit) {
    return { truncated: text, wasTruncated: false }
  }
  // Pega o último espaço antes de `limit` pra não cortar palavra no meio
  const slice = text.slice(0, limit)
  const lastSpace = slice.lastIndexOf(' ')
  const cutAt = lastSpace > limit * 0.6 ? lastSpace : limit // se não achar espaço perto, corta seco
  return {
    truncated: text.slice(0, cutAt).trimEnd() + '...',
    wasTruncated: true,
  }
}

export function MessageBubble({ role, content, model, tokens, thinking, collapseEnabled = true, isPendingQuestion = false, pendingAttrLabel = null, timestamp = null }: MessageBubbleProps) {
  const isUser = role === 'user'
  const ref = useRef<HTMLDivElement>(null)
  // Sistema 2: perguntas de onboarding pendente com fundo amarelo chamativo
  const isYellowNote = !isUser && isPendingQuestion

  // Quem pode ver metadata técnica: só admin
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'SUPER_ADMIN'

  // Feature "Ver mais/menos" — só faz sentido pra mensagens da Ayria (não user)
  // Admin sempre começa expandido (sem precisar clicar)
  // Se collapseEnabled=false → mostra tudo sempre (controle global no header)
  const [expanded, setExpanded] = useState(isAdmin)

  // Se o user virar admin em runtime (improvável mas possível), sincroniza
  useEffect(() => {
    if (isAdmin) setExpanded(true)
  }, [isAdmin])

  const showCollapseButton =
    collapseEnabled && !isUser && !isAdmin && content.length > COLLAPSE_THRESHOLD_CHARS
  const { truncated } = showCollapseButton && !expanded
    ? truncateAtWord(content, COLLAPSE_THRESHOLD_CHARS)
    : { truncated: content }
  const displayContent = truncated

  return (
    <div
      ref={ref}
      className={`flex w-full mb-3 sm:mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[95%] sm:max-w-[88%] rounded-2xl px-4 py-3 sm:px-5 sm:py-4 break-words ${
          isUser ? 'text-white' : 'text-ayria-text'
        }`}
        style={
          isUser
            ? { background: 'linear-gradient(135deg, #f1c961, #da950b)' }
            : isYellowNote
              ? {
                  // ⚠️ DESTAQUE AMARELO: pergunta pendente do onboarding (Sistema 2)
                  background: 'linear-gradient(135deg, rgba(251, 191, 36, 0.18), rgba(245, 158, 11, 0.12))',
                  border: '1.5px solid rgba(251, 191, 36, 0.55)',
                  boxShadow: '0 0 16px rgba(251, 191, 36, 0.25)',
                }
              : {
                  background: '#111111',
                  border: '1px solid rgba(99, 102, 241, 0.2)',
                }
        }
      >
        {/* BADGE PENDENTE — só aparece quando é pergunta pendente de onboarding */}
        {!isUser && isYellowNote && (
          <div
            className="flex items-center gap-1.5 mb-2 text-[11px] font-bold uppercase tracking-wider"
            style={{ color: '#FBBF24' }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 2L1 21h22L12 2zm0 6l7.5 13h-15L12 8zm-1 4v3h2v-3h-2zm0 5v2h2v-2h-2z"/>
            </svg>
            <span>Pergunta pendente{pendingAttrLabel ? ` — ${pendingAttrLabel}` : ''}</span>
          </div>
        )}
        {/* Header: só pra admin */}
        {!isUser && isAdmin && (
          <div className="flex items-center gap-2 mb-2 text-xs text-ayria-muted">
            <LogoIcon size={12} variant="circular" />
            <span>AYRIA</span>
            {model && <span className="opacity-60">· {model}</span>}
            {tokens && <span className="opacity-60">· {tokens} tokens</span>}
          </div>
        )}

        {/* Thinking: só pra admin (raciocínio vazado pelo modelo) */}
        {!isUser && isAdmin && thinking && (
          <details className="mb-3 text-xs">
            <summary className="cursor-pointer text-ayria-muted hover:text-ayria-primary flex items-center gap-1 select-none">
              <Brain size={11} />
              <span>Raciocínio interno (vazado pelo modelo)</span>
            </summary>
            <pre className="mt-2 p-2 rounded bg-black/40 text-ayria-muted whitespace-pre-wrap text-[11px] leading-relaxed border border-ayria-primary/10">
              {thinking}
            </pre>
          </details>
        )}

        <div
          className="markdown text-[15px] sm:text-[17px] leading-relaxed"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(displayContent) }}
        />

        {/* Rodapé: timestamp (dia/hora) — aparece em user e assistant */}
        {timestamp && (
          <div
            className={`mt-2 text-[10px] tracking-wide ${
              isUser ? 'text-white/65' : 'text-ayria-muted'
            }`}
            title={timestamp}
          >
            {formatBubbleTimestamp(timestamp)}
          </div>
        )}

        {/* Botão "Ver mais" / "Ver menos" */}
        {showCollapseButton && (
          <button
            onClick={() => setExpanded((e) => !e)}
            className="mt-2 inline-flex items-center gap-1 text-xs font-medium text-ayria-primary hover:text-ayria-accent transition-colors"
            style={{ padding: 0 }}
          >
            {expanded ? (
              <>
                <ChevronUp size={14} />
                Ver menos
              </>
            ) : (
              <>
                <ChevronDown size={14} />
                Ver mais
              </>
            )}
          </button>
        )}
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div className="flex w-full mb-3 sm:mb-4 justify-start">
      <div
        className="max-w-[95%] sm:max-w-[88%] rounded-2xl px-4 py-3 sm:px-5 sm:py-4 flex items-center gap-3"
        style={{
          background: '#111111',
          border: '1px solid rgba(99, 102, 241, 0.2)',
        }}
      >
        <LogoIcon size={28} variant="circular" />
        <div className="flex items-center gap-1">
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#f1c961' }}
          />
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#f1c961' }}
          />
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#f1c961' }}
          />
        </div>
      </div>
    </div>
  )
}