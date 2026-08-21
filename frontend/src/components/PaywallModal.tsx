/**
 * AYRIA - Paywall Modal (20/08/2026 v2)
 *
 * Aparece quando o user tenta mandar mensagem sem creditos (402).
 * Copy clara explicando por que fechou + UNICO CTA: "Ver os planos".
 *
 * Sem cards clicáveis individuais — força user a ir pra /planos
 * e ver os detalhes completos de cada plano.
 */
import { useNavigate } from 'react-router-dom'

interface PaywallModalProps {
  isOpen: boolean
  onClose: () => void
}

export function PaywallModal({ isOpen, onClose }: PaywallModalProps) {
  const navigate = useNavigate()

  if (!isOpen) return null

  function handleViewPlans() {
    onClose()
    navigate('/planos')
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(4px)' }}
      onClick={onClose}
    >
      <div
        className="w-full max-w-md rounded-2xl p-8 relative"
        style={{
          background: 'linear-gradient(135deg, #1a0a2e, #0a0518)',
          border: '1px solid rgba(168, 85, 247, 0.3)',
          boxShadow: '0 0 60px rgba(168, 85, 247, 0.2)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Close */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-ayria-muted hover:text-white text-2xl leading-none"
          aria-label="Fechar"
        >
          ×
        </button>

        {/* Ícone */}
        <div className="text-center mb-4">
          <div className="text-5xl mb-3">🔒</div>
        </div>

        {/* Título */}
        <h2 className="text-2xl font-bold text-white text-center mb-3">
          Suas conversas foram pausadas
        </h2>

        {/* Copy explicativa */}
        <p className="text-ayria-muted text-center mb-2 leading-relaxed">
          Seu período de uso gratuito terminou e o chat foi pausado
          pra você não acumular cobranças inesperadas.
        </p>
        <p className="text-ayria-muted text-center mb-6 leading-relaxed">
          Escolha um plano pra continuar explorando sua Alma Numerológica
          sem limites.
        </p>

        {/* CTA único */}
        <button
          onClick={handleViewPlans}
          className="w-full py-3 rounded-lg font-semibold text-white text-base transition hover:opacity-90 mb-2"
          style={{ background: 'linear-gradient(90deg, #da950b, #f1c961)' }}
        >
          Ver os planos
        </button>
        <button
          onClick={onClose}
          className="w-full py-2 text-ayria-muted hover:text-white text-sm"
        >
          Agora não
        </button>

        <p className="text-center text-xs text-ayria-muted mt-4">
          💳 Cancele quando quiser. Sem fidelidade.
        </p>
      </div>
    </div>
  )
}
