/**
 * AYRIA - Numerology Reveal Page
 *
 * Tela mostrada IMEDIATAMENTE APÓS completar o onboarding.
 * Mostra o mapa numerológico calculado de forma cinematográfica.
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogoIcon } from '../components/Logo'
import { Sparkles, ArrowRight } from 'lucide-react'

interface NumerologyData {
  caminho_vida?: { numero: number; eh_mestre: boolean; calculo?: string }
  expressao?: { numero: number; eh_mestre: boolean }
  alma?: { numero: number }
  personalidade?: { numero: number }
  ano_pessoal?: { numero: number; ano: number; calculo?: string }
}

const INTERPRETACOES: Record<number, { emoji: string; palavras: string[]; resumo: string }> = {
  1: { emoji: '⚡', palavras: ['Liderança', 'Iniciativa', 'Pioneirismo'], resumo: 'Você veio pra abrir caminhos. Onde outros esperam, você age.' },
  2: { emoji: '🌙', palavras: ['Cooperação', 'Diplomacia', 'Sensibilidade'], resumo: 'Você prospera em parcerias. Onde há tensão, você traz equilíbrio.' },
  3: { emoji: '✨', palavras: ['Criatividade', 'Comunicação', 'Alegria'], resumo: 'Você é expressão pura. Sua presença ilumina qualquer ambiente.' },
  4: { emoji: '🏛️', palavras: ['Estabilidade', 'Disciplina', 'Construção'], resumo: 'Você constrói o que dura. Bases sólidas, legado real.' },
  5: { emoji: '🦋', palavras: ['Liberdade', 'Versatilidade', 'Aventura'], resumo: 'Você precisa de movimento. Liberdade é sua essência.' },
  6: { emoji: '💜', palavras: ['Amor', 'Família', 'Cuidado'], resumo: 'Você cuida com amor. Onde você está, há lar.' },
  7: { emoji: '🔮', palavras: ['Sabedoria', 'Introspecção', 'Análise'], resumo: 'Você busca profundidade. A verdade mora no silêncio.' },
  8: { emoji: '👑', palavras: ['Poder', 'Ambição', 'Autoridade'], resumo: 'Você veio pra realizar. Mundo material é seu palco.' },
  9: { emoji: '🌍', palavras: ['Humanitarismo', 'Compaixão', 'Idealismo'], resumo: 'Você serve ao todo. Seu coração abraça a humanidade.' },
  11: { emoji: '🌟', palavras: ['Intuição', 'Inspiração', 'Visão'], resumo: 'Número mestre. Sua intuição é seu superpoder.' },
  22: { emoji: '🏗️', palavras: ['Construtor Mestre', 'Legado', 'Visão Prática'], resumo: 'O mais poderoso dos mestres. Você constrói o impossível.' },
  33: { emoji: '💗', palavras: ['Mestre Curador', 'Amor Total'], resumo: 'A expressão mais alta do amor. Você cura só por existir.' },
}

function NumeroCard({
  titulo,
  data,
  delay = 0,
}: {
  titulo: string
  data?: { numero: number; eh_mestre?: boolean }
  delay?: number
}) {
  if (!data) return null
  const interp = INTERPRETACOES[data.numero]
  const classe = data.eh_mestre ? 'mestre' : ''

  return (
    <div
      className={`numero-card ${classe}`}
      style={{
        animationDelay: `${delay}ms`,
      }}
    >
      <div className="text-xs uppercase tracking-widest text-ayria-muted mb-2">
        {titulo}
      </div>
      <div className="flex items-center gap-3 mb-3">
        <div className="text-5xl">{interp?.emoji || '✨'}</div>
        <div>
          <div className="text-5xl font-bold gradient-text">
            {data.numero}
          </div>
          {data.eh_mestre && (
            <div className="text-xs text-ayria-accent uppercase tracking-wider mt-1">
              ⭐ Mestre
            </div>
          )}
        </div>
      </div>
      <div className="text-sm text-ayria-text mb-2">{interp?.resumo}</div>
      <div className="flex flex-wrap gap-1">
        {interp?.palavras.map((p) => (
          <span
            key={p}
            className="text-xs px-2 py-1 rounded-full"
            style={{
              background: 'rgba(99, 102, 241, 0.15)',
              color: '#A5B4FC',
              border: '1px solid rgba(99, 102, 241, 0.2)',
            }}
          >
            {p}
          </span>
        ))}
      </div>

      <style>{`
        .numero-card {
          background: linear-gradient(180deg, #111111, #0a0a0a);
          border: 1px solid rgba(99, 102, 241, 0.2);
          border-radius: 16px;
          padding: 20px;
          opacity: 0;
          animation: slideInUp 0.6s ease-out forwards;
          transition: transform 0.2s, box-shadow 0.2s;
        }
        .numero-card.mestre {
          border-color: rgba(168, 85, 247, 0.4);
          box-shadow: 0 0 32px rgba(168, 85, 247, 0.2);
        }
        .numero-card:hover {
          transform: translateY(-2px);
          box-shadow: 0 8px 24px rgba(99, 102, 241, 0.2);
        }
        @keyframes slideInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}

export function NumerologyReveal() {
  const navigate = useNavigate()
  const [numerology, setNumerology] = useState<NumerologyData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('http://localhost:8000/api/onboarding/numerology', {
      headers: { Authorization: `Bearer ${localStorage.getItem('ayria_token')}` },
    })
      .then((r) => r.json())
      .then((data) => {
        setNumerology(data.mapa)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: '#050505' }}>
        <div className="text-ayria-muted">Calculando seu mapa...</div>
      </div>
    )
  }

  if (!numerology) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: '#050505' }}>
        <div className="text-center">
          <LogoIcon size={80} variant="circular" className="justify-center mb-4" />
          <p className="text-ayria-muted">Mapa não encontrado. Continuando...</p>
          <button
            onClick={() => navigate('/chat')}
            className="mt-4 px-6 py-2 rounded-xl text-white"
            style={{ background: 'linear-gradient(135deg, #6366F1, #A855F7)' }}
          >
            Ir pro chat
          </button>
        </div>
      </div>
    )
  }

  return (
    <div
      className="min-h-screen px-4 py-12 overflow-y-auto"
      style={{ background: '#050505' }}
    >
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <LogoIcon size={100} variant="circular" className="justify-center mb-6" />
          <div className="flex items-center justify-center gap-2 mb-3">
            <Sparkles size={16} className="text-ayria-accent" />
            <span className="text-xs uppercase tracking-[0.3em] text-ayria-accent">
              Mapa Numerológico Calculado
            </span>
            <Sparkles size={16} className="text-ayria-accent" />
          </div>
          <h1 className="text-4xl font-bold mb-3 gradient-text">
            Sua essência revelada
          </h1>
          <p className="text-ayria-muted max-w-2xl mx-auto">
            Os números que regem sua jornada. Cada um deles carrega padrões que se
            repetem na sua vida — em escolhas, desafios e potenciais.
          </p>
        </div>

        {/* Cards de números */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          <NumeroCard titulo="Caminho de Vida" data={numerology.caminho_vida} delay={100} />
          <NumeroCard titulo="Expressão" data={numerology.expressao} delay={200} />
          <NumeroCard titulo="Alma" data={numerology.alma} delay={300} />
          <NumeroCard titulo="Personalidade" data={numerology.personalidade} delay={400} />
          {numerology.ano_pessoal && (
            <div className="md:col-span-2">
              <NumeroCard titulo={`Ano Pessoal ${numerology.ano_pessoal.ano || ''}`} data={numerology.ano_pessoal} delay={500} />
            </div>
          )}
        </div>

        {/* CTA */}
        <div className="text-center">
          <p className="text-ayria-muted mb-6 max-w-xl mx-auto">
            Esse é só o começo. A AYRIA vai usar esse mapa pra te conhecer melhor a
            cada conversa. <strong className="text-ayria-text">Bora começar?</strong>
          </p>
          <button
            onClick={() => navigate('/chat')}
            className="inline-flex items-center gap-2 px-8 py-4 rounded-2xl text-white font-semibold text-lg transition-opacity hover:opacity-90"
            style={{
              background: 'linear-gradient(135deg, #6366F1, #A855F7)',
              boxShadow: '0 0 32px rgba(99, 102, 241, 0.4)',
            }}
          >
            Conversar com AYRIA
            <ArrowRight size={20} />
          </button>
        </div>
      </div>
    </div>
  )
}