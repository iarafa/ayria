import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Logo, LogoIcon } from '../components/Logo'
import { Check } from 'lucide-react'

/**
 * AYRIA - Criando seu perfil (tela cinematográfica)
 *
 * Mínimo de 30s garantido, mesmo se backend terminar antes.
 * Tela final com "Estou pronto, vamos começar?" + botão OK.
 */

// 9 fases narrativas pra cobrir bem os 30s (~3.3s cada)
const FASES = [
  { texto: "✨ Mapeando suas energias cósmicas", icone: "🌙" },
  { texto: "🔮 Calculando seu caminho numerológico", icone: "🔢" },
  { texto: "♈ Decifrando seu mapa astral completo", icone: "⭐" },
  { texto: "🌟 Posicionando planetas e signos", icone: "🪐" },
  { texto: "🎭 Identificando seu ascendente e lua", icone: "🌗" },
  { texto: "🧬 Sincronizando sua essência única", icone: "💫" },
  { texto: "💎 Calibrando seu tom personalizado", icone: "🎨" },
  { texto: "🌌 Conectando você ao universo AYRIA", icone: "✨" },
  { texto: "⚡ Quase lá... finalizando", icone: "💜" },
]

const DURACAO_POR_FASE_MS = 3300      // 9 fases × 3.3s = ~30s
const MINIMO_TELA_MS = 30000           // nunca menos que 30s
const TIMEOUT_SEGURANCA_MS = 90000     // 90s safety net

export default function CreatingProfilePage() {
  const navigate = useNavigate()
  const [faseAtual, setFaseAtual] = useState(0)
  const [dots, setDots] = useState('')
  const [progressoReal, setProgressoReal] = useState(0)  // 0-100 do backend
  const [pronto, setPronto] = useState(false)             // backend terminou + mínimo passou
  const startedAtRef = useRef(Date.now())

  // ======== Animação das fases narrativas (sempre avança, independente do backend) ========
  useEffect(() => {
    if (pronto) return  // para de avançar quando mostra tela final
    if (faseAtual >= FASES.length) return
    const timer = setTimeout(() => {
      setFaseAtual((f) => Math.min(f + 1, FASES.length))
    }, DURACAO_POR_FASE_MS)
    return () => clearTimeout(timer)
  }, [faseAtual, pronto])

  // ======== Animação dos "..." ========
  useEffect(() => {
    if (pronto) return
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? '' : d + '.'))
    }, 400)
    return () => clearInterval(interval)
  }, [pronto])

  // ======== Polling backend + gate de 30s mínimo ========
  useEffect(() => {
    let ativo = true
    const startedAt = Date.now()
    startedAtRef.current = startedAt

    const poll = async () => {
      if (!ativo) return

      const elapsed = Date.now() - startedAt
      const backendPronto = await (async () => {
        try {
          const { data } = await api.get('/api/onboarding/profile/status')
          setProgressoReal(data.profile_status === 'ready' ? 100 : data.profile_status === 'failed' ? 50 : 30)
          return data.profile_status === 'ready' || data.profile_status === 'failed'
        } catch {
          return false
        }
      })()

      // GATE: backend pronto E passou 30s mínimo
      if (backendPronto && elapsed >= MINIMO_TELA_MS) {
        setPronto(true)
        return
      }

      // Safety net: passou 90s → libera mesmo assim
      if (elapsed > TIMEOUT_SEGURANCA_MS) {
        console.warn('Profile timeout total - liberando')
        setPronto(true)
        return
      }

      // Continua polling
      const interval = backendPronto ? 2000 : 800
      if (ativo) setTimeout(poll, interval)
    }

    poll()
    return () => { ativo = false }
  }, [])

  // ======== Handlers ========
  const handleComecar = () => {
    navigate('/chat')
  }

  // ======== TELA FINAL: "estou pronto, vamos começar?" ========
  if (pronto) {
    return (
      <div
        className="min-h-screen flex flex-col items-center justify-center px-6"
        style={{ background: 'radial-gradient(ellipse at center, #1a0a2e 0%, #050505 70%)' }}
      >
        {/* Estrelas de fundo */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          {[...Array(50)].map((_, i) => (
            <div
              key={i}
              className="absolute rounded-full"
              style={{
                left: `${(i * 37) % 100}%`,
                top: `${(i * 53) % 100}%`,
                width: `${(i % 3) + 1}px`,
                height: `${(i % 3) + 1}px`,
                background: '#fff',
                opacity: 0.3 + (i % 5) * 0.1,
                animation: `pulse ${2 + (i % 4)}s ease-in-out infinite`,
                animationDelay: `${(i * 0.2) % 3}s`,
              }}
            />
          ))}
        </div>

        <style>{`
          @keyframes pulse {
            0%, 100% { opacity: 0.3; }
            50% { opacity: 0.9; }
          }
          @keyframes glowSuccess {
            0%, 100% { box-shadow: 0 0 60px rgba(99, 102, 241, 0.5), 0 0 120px rgba(168, 85, 247, 0.3); }
            50% { box-shadow: 0 0 100px rgba(99, 102, 241, 0.8), 0 0 200px rgba(168, 85, 247, 0.5); }
          }
          @keyframes scaleIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
          }
          @keyframes fadeUp {
            from { opacity: 0; transform: translateY(20px); }
            to { opacity: 1; transform: translateY(0); }
          }
        `}</style>

        <div className="relative z-10 max-w-md w-full text-center" style={{ animation: 'scaleIn 0.8s ease-out' }}>
          {/* LOGO com glow maior */}
          <div
            className="mx-auto mb-10"
            style={{
              animation: 'glowSuccess 3s ease-in-out infinite',
            }}
          >
            <LogoIcon size={220} variant="circular" />
          </div>

          {/* TÍTULO */}
          <h1
            className="text-5xl font-bold mb-6 gradient-text"
            style={{ animation: 'fadeUp 1s ease-out 0.3s both' }}
          >
            Estou pronto ✨
          </h1>

          {/* SUBTÍTULO */}
          <p
            className="text-ayria-text text-xl mb-3"
            style={{ animation: 'fadeUp 1s ease-out 0.5s both' }}
          >
            Vamos começar?
          </p>

          <p
            className="text-ayria-muted text-sm mb-12 px-8"
            style={{ animation: 'fadeUp 1s ease-out 0.7s both' }}
          >
            Seu perfil único foi criado a partir das estrelas,
            <br />
            dos números e da sua essência.
            <br />
            <span className="text-ayria-primary">AYRIA está te esperando.</span>
          </p>

          {/* BOTÃO OK */}
          <button
            onClick={handleComecar}
            className="px-12 py-4 rounded-full font-semibold text-white text-lg transition-all hover:scale-105 active:scale-95"
            style={{
              background: 'linear-gradient(135deg, #6366F1, #A855F7)',
              boxShadow: '0 0 40px rgba(99, 102, 241, 0.5)',
              animation: 'fadeUp 1s ease-out 0.9s both',
            }}
          >
            OK, vamos lá →
          </button>
        </div>
      </div>
    )
  }

  // ======== TELA DE LOADING (9 fases, mínimo 30s) ========
  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6"
      style={{ background: 'radial-gradient(ellipse at center, #1a0a2e 0%, #050505 70%)' }}
    >
      {/* ESTRELAS DE FUNDO */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(40)].map((_, i) => (
          <div
            key={i}
            className="absolute rounded-full"
            style={{
              left: `${(i * 37) % 100}%`,
              top: `${(i * 53) % 100}%`,
              width: `${(i % 3) + 1}px`,
              height: `${(i % 3) + 1}px`,
              background: '#fff',
              opacity: 0.3 + (i % 5) * 0.1,
              animation: `pulse ${2 + (i % 4)}s ease-in-out infinite`,
              animationDelay: `${(i * 0.2) % 3}s`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; }
          50% { opacity: 0.9; }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 40px rgba(99, 102, 241, 0.4); }
          50% { box-shadow: 0 0 80px rgba(168, 85, 247, 0.7); }
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>

      {/* CONTAINER PRINCIPAL */}
      <div className="relative z-10 max-w-md w-full text-center">

        {/* LOGO/ÍCONE */}
        <div
          className="mx-auto mb-8"
          style={{ animation: 'glow 3s ease-in-out infinite' }}
        >
          <LogoIcon size={180} variant="circular" />
        </div>

        {/* TÍTULO */}
        <h1 className="text-4xl font-bold mb-2 gradient-text">
          Criando seu perfil
        </h1>
        <p className="text-ayria-muted text-sm mb-12">
          Aguarde enquanto preparamos sua jornada única
        </p>

        {/* FASE ATUAL */}
        <div className="h-20 flex items-center justify-center mb-8">
          {faseAtual < FASES.length ? (
            <p
              key={faseAtual}
              className="text-ayria-text text-lg font-medium"
              style={{ animation: 'fadeIn 0.6s ease-out' }}
            >
              {FASES[faseAtual].texto}{dots}
            </p>
          ) : (
            <p
              className="text-white text-xl font-bold flex items-center gap-2"
              style={{ animation: 'fadeIn 0.5s ease-out' }}
            >
              ✨ Tudo pronto! ✨
            </p>
          )}
        </div>

        {/* BARRA DE PROGRESSO */}
        <div
          className="w-full h-2 rounded-full overflow-hidden mb-8"
          style={{ background: '#1E1E2E' }}
        >
          <div
            className="h-full rounded-full"
            style={{
              background: 'linear-gradient(90deg, #6366F1, #A855F7)',
              width: `${Math.min(100, ((faseAtual + 1) / FASES.length) * 100)}%`,
              transition: 'width 0.6s ease-out',
            }}
          />
        </div>

        {/* INDICADORES DE FASES */}
        <div className="flex justify-center gap-2 mb-8">
          {FASES.map((_, i) => (
            <div
              key={i}
              className="w-2 h-2 rounded-full transition-all"
              style={{
                background: i <= faseAtual ? '#6366F1' : '#1E1E2E',
                transform: i === faseAtual ? 'scale(1.4)' : 'scale(1)',
              }}
            />
          ))}
        </div>

        {/* SUBTÍTULO */}
        <p className="text-ayria-muted text-xs">
          Decifrando as energias do seu momento de nascimento...
          <br />
          <span className="text-ayria-primary">Isso é especial, só um instante.</span>
        </p>
      </div>
    </div>
  )
}