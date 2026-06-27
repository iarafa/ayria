/**
 * AYRIA - Message Input
 */
import { useState } from 'react'
import { Send } from 'lucide-react'

interface MessageInputProps {
  onSend: (text: string) => void
  disabled?: boolean
}

export function MessageInput({ onSend, disabled }: MessageInputProps) {
  const [text, setText] = useState('')

  const handleSend = () => {
    if (!text.trim() || disabled) return
    onSend(text.trim())
    setText('')
  }

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-6">
      <div
        className="flex items-end gap-2 rounded-2xl p-2"
        style={{
          background: '#111111',
          border: '1px solid #1E1E2E',
        }}
      >
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="Pergunte algo à AYRIA..."
          rows={1}
          disabled={disabled}
          className="flex-1 bg-transparent text-ayria-text placeholder-ayria-muted resize-none outline-none px-3 py-2"
          style={{ maxHeight: 200, fontFamily: 'Inter, sans-serif' }}
        />
        <button
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          className="p-2 rounded-xl text-white disabled:opacity-30 transition-opacity hover:opacity-90"
          style={{
            background: 'linear-gradient(135deg, #6366F1, #A855F7)',
          }}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  )
}
