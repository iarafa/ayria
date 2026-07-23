/**
 * AYRIA - Onboarding Page (FLUXO ORIGINAL RESTAURADO)
 *
 * Sistema 1 (Pular/Responder depois) foi DESATIVADO conforme pedido do Rafael.
 * Tudo agora é feito NO CHAT via IA (Sistema 2) — não tem mais botões de skip aqui.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { onboardingApi, OnboardingQuestion } from '../lib/api'
import { LogoIcon } from '../components/Logo'
import { ChevronRight, ChevronLeft, Check } from 'lucide-react'
import { useAuth } from '../store/auth'

export function OnboardingPage() {
  const navigate = useNavigate()
  const { loadUser, user } = useAuth()
  const [questions, setQuestions] = useState<OnboardingQuestion[]>([])
  const [currentIdx, setCurrentIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)

  // 🛡️ BYPASS ADMIN: se for admin OU já completou, redireciona
  useEffect(() => {
    if (!user) return  // ainda carregando
    const isAdmin = user.role === 'SUPER_ADMIN' || user.role === 'admin'
    const isCompleted = user.onboarding_status === 'completed'
    if (isAdmin) {
      console.log('🛡️ Admin detectado, redirecionando pra /admin')
      navigate('/admin', { replace: true })
      return
    }
    if (isCompleted) {
      console.log('✅ Onboarding já completed, redirecionando pra /chat')
      navigate('/chat', { replace: true })
      return
    }
  }, [user, navigate])

  useEffect(() => {
    console.log('🔵 [OnboardingPage] mounted, user:', window.location.pathname)

    // PRIMEIRO: atualiza o user no store pra garantir que onboarding_status tá sincronizado
    loadUser()
      .then(() => {
        console.log('🔵 [OnboardingPage] loadUser OK')
        return onboardingApi.status()
      })
      .then((r) => {
        console.log('🔵 [OnboardingPage] status:', r.data?.status, 'perguntas:', r.data?.questions?.length)
        // 🛡️ Backend diz completed → redireciona
        if (r.data?.status === 'completed') {
          const isAdmin = user?.role === 'SUPER_ADMIN' || user?.role === 'admin'
          console.log(isAdmin ? '🛡️ status=completed (admin) → /admin' : '✅ status=completed (user) → /chat')
          navigate(isAdmin ? '/admin' : '/chat', { replace: true })
          return
        }
        // Sem perguntas pendentes (e não completed?) → criando perfil
        if (!r.data?.questions || r.data.questions.length === 0) {
          console.log('🔵 [OnboardingPage] sem perguntas → /criando-perfil')
          navigate('/criando-perfil', { replace: true })
          return
        }
        setQuestions(r.data.questions)
      })
      .catch((e) => {
        console.warn('🔵 [OnboardingPage] falhou:', e)
        setQuestions([])
      })
      .finally(() => {
        console.log('🔵 [OnboardingPage] finally setLoading(false)')
        setLoading(false)
      })
  }, [])

  // Recarrega perguntas e decide se vai pra tela cinematográfica ou continua onboarding
  const reloadQuestions = async () => {
    const r = await onboardingApi.status()
    const remaining = r.data.questions || []
    if (remaining.length === 0) {
      // Todas respondidas/puladas/adiadas → vai pra tela cinematográfica (30s)
      await loadUser()
      navigate('/criando-perfil')
    } else {
      // Continua onboarding do começo com as que faltam
      setQuestions(remaining)
      setCurrentIdx(0)
      setAnswers({})
    }
  }

  const current = questions[currentIdx]
  const progress = questions.length > 0 ? ((currentIdx + 1) / questions.length) * 100 : 0

  const setAnswer = (value: any) => {
    if (!current) return
    setAnswers({ ...answers, [current.attribute_code || current.step]: value })
  }

  const handleNext = async () => {
    if (!current) return
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
      await reloadQuestions()
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
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-ayria-muted opacity-30">
          OnboardingPage.tsx:91
        </div>
      </div>
    )
  }

  if (questions.length === 0) {
    // Lista vazia → user já tem tudo terminal (answered/skipped/pending_next_chat)
    // Vai direto pro chat — sem tela intermediária
    navigate('/chat')
    return null
  }

  return (
    <div
      className="min-h-screen flex flex-col items-center px-4 py-12"
      style={{ background: '#050505' }}
    >
      <div className="w-full max-w-2xl">
        <div className="flex justify-center mb-8">
          <LogoIcon size={64} variant="circular" />
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
                background: 'linear-gradient(90deg, #f1c961, #da950b)',
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

        {/* Botões: Voltar / Pular / Responder Depois / Próximo */}
        <div className="flex justify-between items-center gap-2">
          <button
            onClick={() => setCurrentIdx(Math.max(0, currentIdx - 1))}
            disabled={currentIdx === 0}
            className="px-4 py-2 rounded-xl text-ayria-muted hover:text-ayria-text disabled:opacity-30 flex items-center gap-2"
          >
            <ChevronLeft size={16} />
            Voltar
          </button>

          {/* Skip / Later — fluxo natural: pula/adia e segue. Sem modal/popup. */}
          <div className="flex gap-2">
            <button
              type="button"
              disabled={submitting}
              onClick={async () => {
                if (!current) return
                setSubmitting(true)
                try {
                  await onboardingApi.answer({
                    question_step: current.step,
                    attribute_code: current.attribute_code,
                    value: null,
                    action: 'skip',
                  })
                  // Recarrega lista (backend filtra perguntas terminais)
                  await reloadQuestions()
                } catch (e) {
                  // silent
                } finally {
                  setSubmitting(false)
                }
              }}
              className="px-3 py-2 rounded-xl text-sm hover:bg-ayria-border/30 disabled:opacity-50"
              style={{
                color: '#94A3B8',
                border: '1px solid #1E1E2E',
              }}
            >
              ⏭ Pular
            </button>
            <button
              type="button"
              disabled={submitting}
              onClick={async () => {
                if (!current) return
                setSubmitting(true)
                try {
                  await onboardingApi.answer({
                    question_step: current.step,
                    attribute_code: current.attribute_code,
                    value: null,
                    action: 'later',
                  })
                  await reloadQuestions()
                } catch (e) {
                  // silent
                } finally {
                  setSubmitting(false)
                }
              }}
              className="px-3 py-2 rounded-xl text-sm hover:bg-ayria-border/30 disabled:opacity-50"
              style={{
                color: '#94A3B8',
                border: '1px solid #1E1E2E',
              }}
            >
              💤 Depois
            </button>
            <button
              onClick={handleNext}
              disabled={submitting}
              className="px-5 py-2 rounded-xl text-white font-semibold flex items-center gap-2 disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #f1c961, #da950b)' }}
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
                background: value === (opt.value ?? opt.label) ? 'rgba(241,201,97,0.1)' : '#0a0a0a',
                border: `1px solid ${value === (opt.value ?? opt.label) ? '#f1c961' : '#1E1E2E'}`,
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
                  background: isSelected ? 'rgba(241,201,97,0.2)' : '#0a0a0a',
                  border: `1px solid ${isSelected ? '#f1c961' : '#1E1E2E'}`,
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