/**
 * AYRIA - Logo component
 *
 * 3 variantes:
 * - <Logo /> ou <Logo showText={false} /> — logo simples (sem bolinha)
 * - <LogoIcon /> — logo simples com glow
 * - <LogoIcon variant="circular" /> — logo NA BOLINHA (badge cyberpunk)
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
 * - variant="plain" (padrão): logo direto com glow opcional
 * - variant="circular": logo NA BOLINHA (badge cyberpunk neon)
 */
export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)
  const src = variant === 'circular'
    ? (err ? '/ayria-logo-circular.png' : '/ayria-logo-circular-solid.png')
    : (err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png')

  return (
    <img
      src={src}
      alt="AYRIA"
      width={size}
      height={size}
      className={className}
      style={glow ? { filter: 'drop-shadow(0 0 16px rgba(99,102,241,0.6))' } : undefined}
      onError={() => setErr(true)}
    />
  )
}