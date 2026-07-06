/**
 * AYRIA - Pending Questions Banner
 *
 * Aparece no topo do chat quando há perguntas pendentes (Sistema 2).
 * Mostra 1 pergunta por vez com botões:
 * - Responder (abre input)
 * - Responder depois (snooze 24h)
 * - Pular (com aviso sobre limitação)
 */
import { useState } from 'react'
import { onboardingApi, PendingQuestion } from '../lib/api'
import { X, Clock, SkipForward, AlertCircle, Check } from 'lucide-react'

interface Props {
  question: PendingQuestion
  onClose: () => void  // fecha o banner (já tratou ou vai tratar depois)
  onResponded: () => void  // callback pra recarregar lista de pendentes
}

export function PendingQuestionsBanner({ question, onClose, onResponded }: Props) {
  const [answer, setAnswer] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [showSkipWarning, setShowSkipWarning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleRespond = async () => {
    if (!answer.trim()) {
      setError('Digite uma resposta primeiro')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      await onboardingApi.respondPending(question.attribute_code, answer)
      onResponded()
      onClose()
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Erro ao salvar resposta')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSkip = () => {
    setShowSkipWarning(true)
  }

  const confirmSkip = async () => {
    setSubmitting(true)
    try {
      await onboardingApi.skipPending(question.attribute_code)
      onResponded()
      onClose()
    } catch (e) {
      setError('Erro ao pular pergunta')
    } finally {
      setSubmitting(false)
    }
  }

  const handleSnooze = async () => {
    setSubmitting(true)
    try {
      await onboardingApi.snoozePending(question.attribute_code, 24)
      onResponded()
      onClose()
    } catch (e) {
      setError('Erro ao adiar')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="mx-3 sm:mx-4 mt-3 mb-2 p-4 rounded-2xl"
      style={{
        background: 'rgba(99, 102, 241, 0.08)',
        border: '1px solid rgba(99, 102, 241, 0.3)',
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0"
            style={{ background: 'rgba(99, 102, 241, 0.2)' }}
          >
            <AlertCircle size={16} style={{ color: '#A855F7' }} />
          </div>
          <div>
            <p className="text-xs font-medium" style={{ color: '#A855F7' }}>
              AYRIA quer te conhecer melhor
            </p>
            <p className="text-sm text-ayria-text mt-0.5">
              {question.question_text}
            </p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="text-ayria-muted hover:text-ayria-text p-1"
          title="Fechar (adiar por agora)"
        >
          <X size={14} />
        </button>
      </div>

      {!showSkipWarning ? (
        <>
          {/* Input de resposta */}
          <input
            type={question.question_type === 'date' ? 'date' : 'text'}
            value={answer}
            onChange={(e) => setAnswer(e.target.value)}
            placeholder="Sua resposta..."
            disabled={submitting}
            className="w-full px-3 py-2 rounded-lg text-sm outline-none mb-2"
            style={{
              background: '#0a0a0a',
              border: '1px solid #1E1E2E',
              color: '#F8FAFC',
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleRespond()
            }}
          />
          {error && (
            <p className="text-xs text-red-400 mb-2">{error}</p>
          )}

          {/* Botões */}
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={handleRespond}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs font-medium flex items-center gap-1.5 transition-opacity hover:opacity-80 disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, #6366F1, #A855F7)',
                color: '#FFFFFF',
              }}
            >
              <Check size={12} />
              Responder
            </button>
            <button
              onClick={handleSnooze}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors hover:bg-[#1a1a1a] disabled:opacity-50"
              style={{
                background: 'rgba(148, 163, 184, 0.05)',
                color: '#94A3B8',
                border: '1px solid rgba(148, 163, 184, 0.15)',
              }}
              title="Adiar por 24h"
            >
              <Clock size={12} />
              Responder depois
            </button>
            <button
              onClick={handleSkip}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors hover:bg-[#1a1a1a] disabled:opacity-50"
              style={{
                background: 'rgba(148, 163, 184, 0.05)',
                color: '#94A3B8',
                border: '1px solid rgba(148, 163, 184, 0.15)',
              }}
            >
              <SkipForward size={12} />
              Pular
            </button>
          </div>
        </>
      ) : (
        <>
          {/* Aviso sobre limitação */}
          <div className="p-3 rounded-lg mb-2" style={{ background: 'rgba(245, 158, 11, 0.08)', border: '1px solid rgba(245, 158, 11, 0.2)' }}>
            <p className="text-xs text-ayria-text leading-relaxed">
              <strong>Sem essa informação</strong>, posso não te interpretar tão bem. A pergunta "{question.question_text}" ajuda a AYRIA a personalizar o que ela fala.
            </p>
            <p className="text-xs text-ayria-muted mt-1">
              Quer continuar mesmo assim, ou prefere responder depois?
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button
              onClick={confirmSkip}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs font-medium transition-colors hover:opacity-80 disabled:opacity-50"
              style={{ background: '#1E1E2E', color: '#F8FAFC' }}
            >
              Continuar sem essa informação
            </button>
            <button
              onClick={handleSnooze}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs flex items-center gap-1.5 transition-colors hover:opacity-80 disabled:opacity-50"
              style={{
                background: 'linear-gradient(135deg, #6366F1, #A855F7)',
                color: '#FFFFFF',
              }}
            >
              <Clock size={12} />
              Responder depois
            </button>
            <button
              onClick={() => setShowSkipWarning(false)}
              disabled={submitting}
              className="px-3 py-1.5 rounded-lg text-xs transition-colors hover:bg-[#1a1a1a]"
              style={{ color: '#94A3B8' }}
            >
              Voltar
            </button>
          </div>
        </>
      )}
    </div>
  )
}