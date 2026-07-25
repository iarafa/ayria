/**
 * admin/tabs/helpers.tsx — Componentes auxiliares reutilizáveis
 *
 * Componentes:
 * - Section (colapsável com ícone)
 * - Field (label + valor com highlight)
 * - Badge (chip colorido)
 * - StatCard (card de estatística)
 * - DataRow (linha com ícone + label + valor)
 * - EmptyState (estado vazio)
 * - NumberCard (numerologia)
 * - PlanetCard (astrologia)
 * - humanizeKey, formatValue, capitalize (utilitários)
 */
import React from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'

export function Section({ title, icon, expanded, onToggle, children }: {
  title: string
  icon: React.ReactNode
  expanded: boolean
  onToggle: () => void
  children: React.ReactNode
}) {
  return (
    <div className="rounded-xl overflow-hidden" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      <button onClick={onToggle} className="w-full px-4 py-3 flex items-center justify-between hover:bg-[#1a1a1a] transition-colors">
        <div className="flex items-center gap-2 text-ayria-text font-semibold">
          {icon}
          {title}
        </div>
        {expanded ? <ChevronDown size={16} className="text-ayria-muted" /> : <ChevronRight size={16} className="text-ayria-muted" />}
      </button>
      {expanded && <div className="px-4 pb-4 pt-1">{children}</div>}
    </div>
  )
}

export function Field({ label, value, highlight }: {
  label: string
  value: any
  highlight?: 'success' | 'danger' | boolean
}) {
  let color = ''
  if (highlight === 'success') color = '#10B981'
  else if (highlight === 'danger') color = '#EF4444'
  else if (highlight === true) color = '#da950b'

  return (
    <div>
      <div className="text-xs text-ayria-muted mb-0.5">{label}</div>
      <div className="text-sm font-medium" style={{ color: color || undefined }}>{value || '-'}</div>
    </div>
  )
}

export function Badge({ color, icon, children }: {
  color: string
  icon?: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-semibold"
      style={{
        background: `${color}20`,
        color: color,
        border: `1px solid ${color}40`,
      }}
    >
      {icon}
      {children}
    </span>
  )
}

export function StatCard({ icon, label, value, subtitle, color }: {
  icon: React.ReactNode
  label: string
  value: any
  subtitle?: string
  color: string
}) {
  return (
    <div
      className="p-4 rounded-xl"
      style={{
        background: `${color}10`,
        border: `1px solid ${color}30`,
      }}
    >
      <div className="flex items-center gap-2 mb-1">
        <div style={{ color }}>{icon}</div>
        <div className="text-xs text-ayria-muted">{label}</div>
      </div>
      <div className="text-xl font-bold" style={{ color }}>{value}</div>
      {subtitle && <div className="text-xs text-ayria-muted mt-0.5">{subtitle}</div>}
    </div>
  )
}

export function DataRow({ icon, label, sublabel, value }: {
  icon?: React.ReactNode
  label: string
  sublabel?: string
  value: any
}) {
  return (
    <div className="flex items-start justify-between gap-3 py-1.5 px-2 rounded hover:bg-[#1a1a1a]">
      <div className="flex items-start gap-2 min-w-0 flex-1">
        {icon && <div className="text-ayria-muted mt-0.5 shrink-0">{icon}</div>}
        <div className="min-w-0">
          <div className="text-xs text-ayria-muted">{label}</div>
          {sublabel && <div className="text-[10px] text-ayria-muted opacity-60">{sublabel}</div>}
        </div>
      </div>
      <div className="text-sm text-ayria-text text-right shrink-0 max-w-[60%] break-words">{value || '-'}</div>
    </div>
  )
}

export function EmptyState() {
  return (
    <div className="p-6 text-center text-ayria-muted rounded-xl" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      Nenhum dado disponível.
    </div>
  )
}

export function NumberCard({ label, numero, ehMestre }: {
  label: string
  numero: number
  ehMestre?: boolean
}) {
  return (
    <div className="p-3 rounded-xl text-center" style={{ background: '#111111', border: '1px solid #1E1E2E' }}>
      <div className="text-xs text-ayria-muted mb-1">{label}</div>
      <div className="text-3xl font-bold" style={{ color: ehMestre ? '#F59E0B' : '#da950b' }}>
        {numero}
      </div>
      {ehMestre && <div className="text-[10px] text-ayria-muted mt-1">Número mestre</div>}
    </div>
  )
}

export function PlanetCard({ nome, signo, elemento, casa, destaque }: {
  nome: string
  signo: string
  elemento?: string
  casa?: number | string
  destaque?: boolean
}) {
  return (
    <div
      className="p-3 rounded-xl"
      style={{
        background: destaque ? 'rgba(241,201,97,0.10)' : '#111111',
        border: destaque ? '1px solid rgba(241,201,97,0.4)' : '1px solid #1E1E2E',
      }}
    >
      <div className="text-xs text-ayria-muted mb-1">{nome}</div>
      <div className="text-lg font-bold text-ayria-text">{signo}</div>
      {elemento && <div className="text-[10px] text-ayria-muted mt-0.5">{elemento}</div>}
      {casa !== undefined && casa !== null && <div className="text-[10px] text-ayria-muted">Casa {casa}</div>}
    </div>
  )
}

export function humanizeKey(key: string): string {
  return key
    .replace(/_/g, ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

export function formatValue(value: any): string {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export function capitalize(s: string): string {
  if (!s) return ''
  return s.charAt(0).toUpperCase() + s.slice(1)
}
