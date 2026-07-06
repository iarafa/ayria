/**
 * AYRIA - Logo component
 *
 * - <Logo /> — logo + texto
 * - <LogoIcon variant="plain" /> — só PNG do logo
 * - <LogoIcon variant="circular" /> — círculo neon do logo, sem caixa/quadrado
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  glow?: boolean
}

export function Logo({ size = 48, showText = true, className = '', glow = true }: LogoProps) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <LogoIcon size={size} variant="circular" glow={glow} />
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

interface LogoIconProps {
  size?: number
  glow?: boolean
  className?: string
  variant?: 'plain' | 'circular'
}

export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  if (variant === 'circular') {
    // SEM container, SEM background, SEM box-shadow, SEM overflow:hidden.
    // O PNG já é circular com cantos transparentes.
    // objectFit: 'contain' garante que o PNG aparece inteiro (sem corte).
    // Cache-bust via query string pra navegador não usar cache antigo.
    const v = '20260629b'
    return (
      <img
        src={`${err ? '/ayria-logo-transparent.png' : '/ayria-logo-circular.png'}?v=${v}`}
        alt="AYRIA"
        width={size}
        height={size}
        className={className}
        style={{
          display: 'block',
          width: size,
          height: size,
          objectFit: 'contain',
          filter: glow ? 'drop-shadow(0 0 12px rgba(99,102,241,0.5))' : undefined,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  return (
    <img
      src={err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png'}
      alt="AYRIA"
      width={size}
      height={size}
      className={className}
      style={glow ? { filter: 'drop-shadow(0 0 16px rgba(99,102,241,0.6))' } : undefined}
      onError={() => setErr(true)}
    />
  )
}