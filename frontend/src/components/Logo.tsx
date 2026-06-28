/**
 * AYRIA - Logo component (com glow)
 *
 * Variações:
 * - <Logo /> — logo + texto "AYRIA" (padrão, sidebar)
 * - <Logo size={120} showText={false} /> — só logo, sem texto (onboarding/login)
 * - <Logo size={32} showText={false} /> — só logo pequeno (header chat, admin)
 * - <LogoIcon size={32} /> — wrapper com fundo gradiente + glow (chat welcome)
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  glow?: boolean  // adiciona drop-shadow glow indigo
}

export function Logo({ size = 48, showText = true, className = '', glow = true }: LogoProps) {
  const [err, setErr] = useState(false)
  const src = err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png'

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src={src}
        alt="AYRIA"
        width={size}
        height={size}
        style={glow ? { filter: 'drop-shadow(0 0 12px rgba(99,102,241,0.4))' } : undefined}
        onError={() => setErr(true)}
      />
      {showText && (
        <span
          className="font-bold tracking-[0.3em] text-ayria-text"
          style={{ fontSize: size * 0.35 }}
        >
          AYRIA
        </span>
      )}
    </div>
  )
}

/**
 * LogoIcon — logo dentro de círculo com gradiente indigo→purple e glow forte.
 * Substitui o Sparkles genérico em headers e welcome screens.
 */
interface LogoIconProps {
  size?: number        // diâmetro do círculo (px)
  className?: string
}

export function LogoIcon({ size = 40, className = '' }: LogoIconProps) {
  const [err, setErr] = useState(false)
  const src = err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png'
  const inner = Math.round(size * 0.6)

  return (
    <div
      className={`rounded-full flex items-center justify-center ${className}`}
      style={{
        width: size,
        height: size,
        background: 'linear-gradient(135deg, #6366F1, #A855F7)',
        boxShadow: '0 0 20px rgba(99, 102, 241, 0.5)',
      }}
    >
      <img
        src={src}
        alt="AYRIA"
        width={inner}
        height={inner}
        style={{
          filter: 'drop-shadow(0 0 4px rgba(255,255,255,0.3))',
          objectFit: 'contain',
        }}
        onError={() => setErr(true)}
      />
    </div>
  )
}
