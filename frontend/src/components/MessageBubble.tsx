/**
 * AYRIA - Message Bubble
 *
 * Mostra APENAS o conteúdo da mensagem para usuários comuns.
 * Para ADMIN/SUPER_ADMIN, mostra também: modelo IA, tokens, e thinking
 * (raciocínio vazado pelo modelo) — info útil pra debug.
 */
import { useEffect, useRef } from 'react'
import { Brain } from 'lucide-react'
import { useAuth } from '../store/auth'
import { LogoIcon } from './Logo'

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  tokens?: number
  thinking?: string | null
}

function renderMarkdown(text: string): string {
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
  // Gradient cyan→magenta→purple (mesmo do anel neon do logo)
  rendered = rendered.replace(
    /\bAYRIA\b/g,
    '<span style="color: #EC4899; font-weight: 700; background: linear-gradient(135deg, #00FFFF, #EC4899); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text; text-shadow: 0 0 12px rgba(236, 72, 153, 0.5);">AYRIA</span>'
  )

  return rendered
}

export function MessageBubble({ role, content, model, tokens, thinking }: MessageBubbleProps) {
  const isUser = role === 'user'
  const ref = useRef<HTMLDivElement>(null)

  // Quem pode ver metadata técnica: só admin
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'SUPER_ADMIN'

  useEffect(() => {
    ref.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [content])

  return (
    <div
      ref={ref}
      className={`flex w-full mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 ${
          isUser ? 'text-white' : 'text-ayria-text'
        }`}
        style={
          isUser
            ? { background: 'linear-gradient(135deg, #6366F1, #A855F7)' }
            : {
                background: '#111111',
                border: '1px solid rgba(99, 102, 241, 0.2)',
              }
        }
      >
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
          className="markdown text-[15px]"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(content) }}
        />
      </div>
    </div>
  )
}

export function TypingIndicator() {
  return (
    <div className="flex w-full mb-4 justify-start">
      <div
        className="max-w-[75%] rounded-2xl px-4 py-3 flex items-center gap-3"
        style={{
          background: '#111111',
          border: '1px solid rgba(99, 102, 241, 0.2)',
        }}
      >
        <LogoIcon size={28} variant="circular" />
        <div className="flex items-center gap-1">
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#6366F1' }}
          />
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#6366F1' }}
          />
          <div
            className="typing-dot w-2 h-2 rounded-full"
            style={{ background: '#6366F1' }}
          />
        </div>
      </div>
    </div>
  )
}
