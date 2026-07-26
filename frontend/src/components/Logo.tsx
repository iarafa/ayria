/**
 * AYRIA - Logo component
 *
 * Logo único do projeto: símbolo circular neon (triângulo + infinito cyan/magenta).
 * SEM texto "AYRIA" em lugar nenhum — Rafael 26/07/2026 mandou padronizar.
 *
 * Variants disponíveis:
 * - 'symbol' (default) — carrega `/ayria-logo-circular.png` (quadrado, neon)
 * - 'wide' — carrega `/ayria-logo-lovable.png` (banner AYRIA + subtítulo, legacy)
 * - 'circular' — alias de 'symbol' (compat com código mais antigo)
 * - 'plain' — alias de 'symbol' (default histórico)
 *
 * Tam padrão recomendado:
 * - Login/Register/AdminLogin/VerifyEmail: 96px (responsivo)
 * - Onboarding/Numerology/CreatingProfile: 96px
 * - PlanosPage header: 80px
 * - Sidebar: 56px
 * - AdminPage header: 32px
 * - MessageBubble (mensagem AI): 20px
 * - ObserveUserPage: 28px
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
  glow?: boolean
}

export function Logo({ size = 96, showText = true, className = '', glow = true }: LogoProps) {
  return (
    <div className={`flex flex-col items-center gap-2 ${className}`}>
      <LogoIcon size={size} variant="symbol" glow={glow} />
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
  variant?: 'plain' | 'wide' | 'circular' | 'symbol'
}

const ASPECT_WIDE = 1536 / 360  // wide banner
const ASPECT_SQUARE = 1          // symbol quadrado

export function LogoIcon({ size = 40, glow = true, className = '', variant = 'symbol' }: LogoIconProps) {
  const [err, setErr] = useState(false)

  // Glow neon (cyan/magenta) — único glow do projeto a partir de 26/07
  const goldGlow = glow
    ? 'drop-shadow(0 0 12px rgba(34,211,238,0.55)) drop-shadow(0 0 24px rgba(236,72,153,0.45)) drop-shadow(0 0 4px rgba(255,255,255,0.4))'
    : undefined

  const maxWidth = size >= 300 ? '90vw' : size >= 150 ? '70vw' : size >= 96 ? '50vw' : undefined

  const isWide = variant === 'wide'
  const width = size
  const height = isWide ? Math.round(size / ASPECT_WIDE) : size

  // 'wide' (legacy): banner AYRIA + subtítulo
  if (isWide) {
    const v = '20260723b'
    return (
      <img
        src={`/ayria-logo-lovable.png?v=${v}`}
        alt="AYRIA"
        width={width}
        height={height}
        className={className}
        style={{
          display: 'block', width, height, maxWidth,
          objectFit: 'contain', filter: goldGlow,
        }}
        onError={() => setErr(true)}
      />
    )
  }

  // 'symbol' (default), 'circular', 'plain' — símbolo circular neon, sem texto
  const v = '20260726a'
  return (
    <img
      src={`/ayria-logo-circular.png?v=${v}`}
      alt="AYRIA"
      width={width}
      height={height}
      className={className}
      style={{
        display: 'block', width, height, maxWidth,
        objectFit: 'contain', filter: goldGlow,
      }}
      onError={() => setErr(true)}
    />
  )
}
