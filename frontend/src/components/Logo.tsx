/**
 * AYRIA - Logo component
 *
 * Visual alinhado com a landing Lovable:
 * - Logo dourado com glow
 * - Texto "AYRIA" em serif (Cormorant Garamond)
 *
 * - <Logo /> — logo + texto
 * - <LogoIcon variant="plain" /> — só PNG do logo
 * - <LogoIcon variant="circular" /> — círculo do logo (com glow dourado)
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
          className="font-display font-medium tracking-[0.18em] gradient-text"
          style={{ fontSize: size * 0.42 }}
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

  // Glow dourado Lovable (substituindo indigo)
  const goldGlow = glow
    ? 'drop-shadow(0 0 14px rgba(241,201,97,0.55)) drop-shadow(0 0 28px rgba(218,149,11,0.35))'
    : undefined

  if (variant === 'circular') {
    // Cache-bust via query string pra navegador não usar cache antigo
    const v = '20260723a'
    return (
      <img
        src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=${v}`}
        alt="AYRIA"
        width={size}
        height={size}
        className={className}
        style={{
          display: 'block',
          width: size,
          height: size,
          objectFit: 'contain',
          filter: goldGlow,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  return (
    <img
      src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=20260723a`}
      alt="AYRIA"
      width={size}
      height={size}
      className={className}
      style={glow ? { filter: goldGlow } : undefined}
      onError={() => setErr(true)}
    />
  )
}
