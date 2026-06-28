import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api'
import { Sparkles, Stars } from 'lucide-react'

const FASES = [
  { texto: "Mapeando suas energias cósmicas...", duracao: 1800 },
  { texto: "Calculando seu caminho numerológico...", duracao: 1600 },
  { texto: "Decifrando seu mapa astral...", duracao: 2000 },
  { texto: "Sincronizando seu perfil único...", duracao: 1400 },
  { texto: "Quase pronto... ✨", duracao: 1200 },
]

export default function CreatingProfilePage() {
  const navigate = useNavigate()
  const [faseAtual, setFaseAtual] = useState(0)
  const [dots, setDots] = useState('')

  // Animação das fases narrativas
  useEffect(() => {
    if (faseAtual >= FASES.length) return
    const timer = setTimeout(() => {
      setFaseAtual((f) => Math.min(f + 1, FASES.length))
    }, FASES[faseAtual].duracao)
    return () => clearTimeout(timer)
  }, [faseAtual])

  // Animação dos "..." (1, 2, 3 dots)
  useEffect(() => {
    const interval = setInterval(() => {
      setDots((d) => (d.length >= 3 ? '' : d + '.'))
    }, 400)
    return () => clearInterval(interval)
  }, [])

  // Polling no backend pra saber quando perfil ficou pronto
  useEffect(() => {
    let ativo = true
    const poll = async () => {
      try {
        const { data } = await api.get('/api/onboarding/profile/status')
        if (data.profile_status === 'ready') {
          // Espera a fase narrativa terminar se ainda não terminou
          setTimeout(() => ativo && navigate('/chat'), 800)
          return
        }
        if (data.profile_status === 'failed') {
          // Mesmo se falhou, deixa entrar no chat (vai funcionar sem perfil)
          setTimeout(() => ativo && navigate('/chat'), 2000)
          return
        }
        // Continua polling
        if (ativo) setTimeout(poll, 800)
      } catch (e) {
        // Erro de rede — continua polling
        if (ativo) setTimeout(poll, 2000)
      }
    }
    poll()
    return () => { ativo = false }
  }, [navigate])

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center px-6"
      style={{ background: 'radial-gradient(ellipse at center, #1a0a2e 0%, #050505 70%)' }}
    >
      {/* ESTRELAS DE FUNDO */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(30)].map((_, i) => (
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
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes glow {
          0%, 100% { box-shadow: 0 0 40px rgba(99, 102, 241, 0.4); }
          50% { box-shadow: 0 0 80px rgba(168, 85, 247, 0.7); }
        }
      `}</style>

      {/* CONTAINER PRINCIPAL */}
      <div className="relative z-10 max-w-md w-full text-center">

        {/* LOGO/ÍCONE */}
        <div
          className="w-32 h-32 mx-auto rounded-full flex items-center justify-center mb-8"
          style={{
            background: 'linear-gradient(135deg, #6366F1, #A855F7)',
            animation: 'glow 3s ease-in-out infinite',
          }}
        >
          <Stars size={56} className="text-white" />
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
              className="text-ayria-text text-lg font-medium animate-fade-in"
              style={{
                animation: 'fadeIn 0.6s ease-out',
              }}
            >
              {FASES[faseAtual].texto}{dots}
            </p>
          ) : (
            <p
              className="text-white text-xl font-bold flex items-center gap-2"
              style={{ animation: 'fadeIn 0.5s ease-out' }}
            >
              <Sparkles size={20} />
              Tudo pronto!
              <Sparkles size={20} />
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
          Estamos decifrando as energias do seu momento de nascimento.
          <br />
          Isso leva só alguns segundos.
        </p>
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}