/**
 * AYRIA - Logo component
 *
 * Visual alinhado com a landing Lovable:
 * - Logo wordmark "AYRIA" com fundo transparente
 * - Texto "AYRIA" do Logo em serif (Cormorant Garamond)
 *
 * Logo wide (aspect 1536:220 ≈ 7:1) — apenas o wordmark,
 * sem o subtítulo "CLAREZA PRA DECIDIR" (que é redundante com H1 da página).
 *
 * - <Logo /> — logo + texto "AYRIA" em gradient
 * - <LogoIcon variant="circular" /> — só PNG do logo wide
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
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <LogoIcon size={size} variant="circular" glow={glow} />
      {showText && (
        <span
          className="font-display font-medium tracking-[0.25em] gradient-text"
          style={{ fontSize: size * 0.14 }}
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

// Logo wide aspect ratio (1536 / 360) — inclui AYRIA + subtítulo + ornamento
// (23/07/2026: Rafael pediu pra restaurar o subtítulo que eu tinha cortado)
const ASPECT_WIDE = 1536 / 360

export function LogoIcon({ size = 40, glow = true, className = '', variant = 'plain' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  // Glow dourado Lovable
  const goldGlow = glow
    ? 'drop-shadow(0 0 14px rgba(241,201,97,0.55)) drop-shadow(0 0 28px rgba(218,149,11,0.35))'
    : undefined

  // Responsivo: limita largura em telas pequenas (mobile)
  const maxWidth = size >= 300 ? '90vw' : size >= 150 ? '70vw' : size >= 80 ? '50vw' : undefined

  // Wide: size = LARGURA. Altura proporcional (size / 7).
  const width = size
  const height = Math.round(size / ASPECT_WIDE)

  if (variant === 'circular') {
    const v = '20260723b'  // cache-bust: wide AYRIA-only
    return (
      <img
        src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=${v}`}
        alt="AYRIA"
        width={width}
        height={height}
        className={className}
        style={{
          display: 'block',
          width,
          height,
          maxWidth,
          objectFit: 'contain',
          filter: goldGlow,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  return (
    <img
      src={`${err ? '/ayria-logo-lovable.png' : '/ayria-logo-lovable.png'}?v=20260723b`}
      alt="AYRIA"
      width={width}
      height={height}
      className={className}
      style={{
        display: 'block',
        maxWidth,
        filter: goldGlow,
      }}
      onError={() => setErr(true)}
    />
  )
}
