/**
 * AYRIA - Logo component (com glow)
 */
import { useState } from 'react'

interface LogoProps {
  size?: number
  showText?: boolean
  className?: string
}

export function Logo({ size = 48, showText = true, className = '' }: LogoProps) {
  const [err, setErr] = useState(false)
  const src = err ? '/ayria-logo-transparent.png' : '/ayria-logo-dark.png'

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <img
        src={src}
        alt="AYRIA"
        width={size}
        height={size}
        style={{ filter: 'drop-shadow(0 0 12px rgba(99,102,241,0.4))' }}
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
