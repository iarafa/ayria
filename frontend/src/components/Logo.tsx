/**
 * AYRIA - Logo component
 *
 * Estrutura:
 * - <Logo /> — logo com texto (sidebar, headers com nome)
 * - <LogoIcon variant="plain" /> — só o PNG do logo
 * - <LogoIcon variant="circular" /> — círculo preto CSS atrás + PNG transparente do logo por cima
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  glow?: boolean
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
        style={glow ? { filter: 'drop-shadow(0 0 12px rgba(99,102,241,0.5))' } : undefined}
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

interface LogoIconProps {
  size?: number
  glow?: boolean
  className?: string
  variant?: 'plain' | 'circular'
}

/**
 * LogoIcon:
 *
 * - variant="plain" (default): só o PNG do logo, com glow opcional
 *
 * - variant="circular": ESTRUTURA EM CAMADAS:
 *   1. <div> circular PRETO via CSS (border-radius: 50%, background: #0A0A0A)
 *   2. <img> do logo TRANSPARENTE (ayria-logo-circular.png) por cima
 *
 *   Resultado: bolinha preta perfeita + anel neon + logo, sem quadrado.
 */
export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  if (variant === 'circular') {
    return (
      <div
        className={className}
        style={{
          width: size,
          height: size,
          borderRadius: '50%',
          background: '#0A0A0A',
          boxShadow: glow
            ? '0 0 20px rgba(99, 102, 241, 0.4), inset 0 0 0 1px rgba(255, 255, 255, 0.05)'
            : 'inset 0 0 0 1px rgba(255, 255, 255, 0.05)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
          flexShrink: 0,
        }}
      >
        <img
          src={err ? '/ayria-logo-transparent.png' : '/ayria-logo-circular.png'}
          alt="AYRIA"
          width={size}
          height={size}
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain',
            filter: glow ? 'drop-shadow(0 0 8px rgba(99,102,241,0.5))' : undefined,
          }}
          onError={() => setErr(true)}
        />
      </div>
    )
  }

  // variant="plain"
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