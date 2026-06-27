/**
 * AYRIA - Onboarding Page
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { onboardingApi, OnboardingQuestion } from '../lib/api'
import { Logo } from '../components/Logo'
import { ChevronRight, ChevronLeft, Check } from 'lucide-react'

export function OnboardingPage() {
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    onboardingApi.status().then((r) => {
      setQuestions(r.data.questions || [])
      setLoading(false)
    })
  }, [])

  const current = questions[currentIdx]
  const progress = questions.length > 0 ? ((currentIdx + 1) / questions.length) * 100 : 0

  const setAnswer = (value: any) => {
    if (!current) return
    setAnswers({ ...answers, [current.attribute_code || current.step]: value })
  }

  const handleNext = async () => {
    if (!current) return
    // Salva resposta atual
    const value = answers[current.attribute_code || current.step]
    if (value === undefined) {
      alert('Por favor responda antes de continuar')
      return
    }
    setSubmitting(true)
    try {
      await onboardingApi.answer({
        question_step: current.step,
        attribute_code: current.attribute_code,
        value,
      })
      if (currentIdx + 1 >= questions.length) {
        navigate('/numerology')
      } else {
        setCurrentIdx(currentIdx + 1)
      }
    } catch (e) {
      alert('Erro ao salvar resposta')
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#050505' }}>
        <div className="text-ayria-muted">Carregando...</div>
      </div>
    )
  }

  if (questions.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#050505' }}>
        <div className="text-center max-w-md">
          <Logo size={120} showText={false} className="justify-center mb-6" />
          <h1 className="text-3xl font-bold mb-3 gradient-text">Tudo pronto!</h1>
          <p className="text-ayria-muted mb-6">
            Você já completou o onboarding. Vamos conversar?
          </p>
          <button
            onClick={() => navigate('/chat')}
            className="px-6 py-3 rounded-xl text-white font-semibold"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            Ir para o Chat
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center px-4 py-12"
      style={{ background: '#050505' }}
    >
      <div className="w-full max-w-2xl">
        <div className="flex justify-center mb-8">
          <Logo size={64} showText={false} />
        </div>

        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex justify-between text-xs text-ayria-muted mb-2">
            <span>Passo {currentIdx + 1} de {questions.length}</span>
            <span>{Math.round(progress)}%</span>
          </div>
          <div className="h-1 rounded-full" style={{ background: '#1E1E2E' }}>
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${progress}%`,
                background: 'linear-gradient(90deg, #6366F1, #A855F7)',
              }}
            />
          </div>
        </div>

        {/* Pergunta */}
        <div
          className="p-8 rounded-2xl mb-6"
          style={{
            background: '#111111',
            border: '1px solid #1E1E2E',
          }}
        >
          <h2 className="text-2xl font-semibold text-ayria-text mb-2">
            {current.question_text}
          </h2>
          {current.helper_text && (
            <p className="text-sm text-ayria-muted mb-6">{current.helper_text}</p>
          )}

          <QuestionInput
            question={current}
            value={answers[current.attribute_code || current.step]}
            onChange={setAnswer}
          />
        </div>

        {/* Botões */}
        <div className="flex justify-between">
          <button
            onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}
            disabled={currentIdx === 0}
            className="px-5 py-2 rounded-xl text-ayria-muted hover:text-ayria-text disabled:opacity-30 flex items-center gap-2"
          >
            <ChevronLeft size={16} />
            Voltar
          </button>
          <button
            onClick={handleNext}
            disabled={submitting}
            className="px-6 py-2 rounded-xl text-white font-semibold flex items-center gap-2 disabled:opacity-50"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            {currentIdx + 1 >= questions.length ? (
              <>
                <Check size={16} />
                {submitting ? 'Finalizando...' : 'Concluir'}
              </>
            ) : (
              <>
                Próximo
                <ChevronRight size={16} />
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  )
}

function QuestionInput({
  question,
  value,
  onChange,
}: {
  question: OnboardingQuestion
  value: any
  onChange: (v: any) => void
}) {
  const baseInputStyle = {
    background: '#0a0a0a',
    border: '1px solid #1E1E2E',
    color: '#F8FAFC',
  }

  switch (question.question_type) {
    case 'text':
      return (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 rounded-xl outline-none"
          style={baseInputStyle}
        />
      )
    case 'textarea':
      return (
        <textarea
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
          className="w-full px-4 py-3 rounded-xl outline-none resize-none"
          style={baseInputStyle}
        />
      )
    case 'date':
      return (
        <input
          type="date"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 rounded-xl outline-none"
          style={baseInputStyle}
        />
      )
    case 'time':
      return (
        <input
          type="time"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 rounded-xl outline-none"
          style={baseInputStyle}
        />
      )
    case 'select':
      const opts = question.options || []
      return (
        <div className="space-y-2">
          {opts.map((opt: any, i: number) => (
            <button
              key={i}
              type="button"
              onClick={() => onChange(opt.value ?? opt.label)}
              className={`w-full text-left px-4 py-3 rounded-xl transition-all ${
                value === (opt.value ?? opt.label)
                  ? 'border-ayria-primary'
                  : 'border-ayria-border'
              }`}
              style={{
                background: value === (opt.value ?? opt.label) ? 'rgba(99,102,241,0.1)' : '#0a0a0a',
                border: `1px solid ${value === (opt.value ?? opt.label) ? '#6366F1' : '#1E1E2E'}`,
              }}
            >
              {opt.label ?? opt.value}
            </button>
          ))}
        </div>
      )
    case 'multiselect':
      const mopts = question.options || []
      const arr: any[] = Array.isArray(value) ? value : []
      return (
        <div className="flex flex-wrap gap-2">
          {mopts.map((opt: any, i: number) => {
            const v = opt.value ?? opt.label
            const isSelected = arr.includes(v)
            return (
              <button
                key={i}
                type="button"
                onClick={() =>
                  onChange(isSelected ? arr.filter((x) => x !== v) : [...arr, v])
                }
                className="px-4 py-2 rounded-xl text-sm transition-all"
                style={{
                  background: isSelected ? 'rgba(99,102,241,0.2)' : '#0a0a0a',
                  border: `1px solid ${isSelected ? '#6366F1' : '#1E1E2E'}`,
                  color: isSelected ? '#F8FAFC' : '#94A3B8',
                }}
              >
                {opt.label ?? opt.value}
              </button>
            )
          })}
        </div>
      )
    default:
      return (
        <input
          type="text"
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-4 py-3 rounded-xl outline-none"
          style={baseInputStyle}
        />
      )
  }
}
