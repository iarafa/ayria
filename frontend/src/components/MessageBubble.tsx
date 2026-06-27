/**
 * AYRIA - Message Bubble
 */
import { useEffect, useRef } from 'react'
import { Sparkles } from 'lucide-react'

interface MessageBubbleProps {
  role: 'user' | 'assistant' | 'system'
  content: string
  model?: string
  tokens?: number
}

function renderMarkdown(text: string): string {
  // Markdown minimalista - bold, italic, code, listas
  return text
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
}

export function MessageBubble({ role, content, model, tokens }: MessageBubbleProps) {
  const isUser = role === 'user'
  const ref = useRef<HTMLDivElement>(null)

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
        {!isUser && (
          <div className="flex items-center gap-2 mb-2 text-xs text-ayria-muted">
            <Sparkles size={12} className="text-ayria-primary" />
            <span>AYRIA</span>
            {model && <span className="opacity-60">· {model}</span>}
            {tokens && <span className="opacity-60">· {tokens} tokens</span>}
          </div>
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
        className="max-w-[75%] rounded-2xl px-4 py-3 flex items-center gap-1"
        style={{
          background: '#111111',
          border: '1px solid rgba(99, 102, 241, 0.2)',
        }}
      >
        <Sparkles size={12} className="text-ayria-primary mr-2" />
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
  )
}
