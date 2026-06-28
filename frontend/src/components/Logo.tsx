/**
 * AYRIA - Logo component
 *
 * Logo direto SEM fundo circular (que ficou visualmente pesado).
 * Glow indigo opcional pra dar destaque no fundo dark.
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

/**
 * LogoIcon — apenas o logo direto, SEM círculo de fundo.
 * Glow indigo opcional pra destacar no fundo dark.
 */
interface LogoIconProps {
  size?: number
  glow?: boolean
  className?: string
}

export function LogoIcon({ size = 40, glow = true, className = '' }: LogoIconProps) {
  const [err, setErr] = useState(false)
  const src = err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png'

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
