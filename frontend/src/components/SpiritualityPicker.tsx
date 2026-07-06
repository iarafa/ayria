/**
 * AYRIA - Spirituality Picker
 *
 * Popover/header que permite user escolher orientação de vida/espiritual.
 * Botão "🙏" no header → popover com lista de religiões → POST no backend
 *
 * Estilo: combina com o resto do app (dark + acento âmbar quando selecionado).
 */

import { useEffect, useRef, useState } from 'react'
import { Church, X, Check, Plus, Trash2 } from 'lucide-react'
import { useAuth } from '../store/auth'

interface ReligionOption {
  value: string
  label: string
  emoji: string
}

interface SpiritualPreference {
  user_id: string
  religion: string
  religion_label?: string
  religion_emoji?: string
  custom_label?: string | null
  custom_tags?: string[]
  notes?: string | null
  is_active?: boolean
}

const API_BASE = import.meta.env.VITE_API_URL || ''

export function SpiritualityPicker() {
  const { token } = useAuth()
  const [open, setOpen] = useState(false)
  const [options, setOptions] = useState<ReligionOption[]>([])
  const [pref, setPref] = useState<SpiritualPreference | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [selectedReligion, setSelectedReligion] = useState<string>('')
  const [customLabel, setCustomLabel] = useState('')
  const popoverRef = useRef<HTMLDivElement>(null)

  const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }

  // Carrega opções + pref quando popover abre
  useEffect(() => {
    if (!open) return
    setLoading(true)
    Promise.all([
      fetch(`${API_BASE}/api/preferences/religion-options`, { headers }).then((r) => r.json()),
      fetch(`${API_BASE}/api/preferences/spiritual`, { headers }).then((r) => r.json()),
    ])
      .then(([opts, current]) => {
        setOptions(opts.options || [])
        if (current && current.religion) {
          setPref(current)
          setSelectedReligion(current.religion)
          setCustomLabel(current.custom_label || '')
        }
      })
      .catch((e) => console.warn('SpiritualityPicker load:', e))
      .finally(() => setLoading(false))
  }, [open, token])

  // Click outside fecha
  useEffect(() => {
    if (!open) return
    const handler = (e: MouseEvent) => {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  const save = async () => {
    if (!selectedReligion) return
    setSaving(true)
    try {
      const r = await fetch(`${API_BASE}/api/preferences/spiritual`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          religion: selectedReligion,
          custom_label: customLabel || null,
          custom_tags: [],
          notes: null,
          is_active: true,
        }),
      })
      if (r.ok) {
        const j = await r.json()
        setPref(j)
        setOpen(false)
      } else {
        const err = await r.text()
        alert(`Erro ao salvar: ${err}`)
      }
    } catch (e: any) {
      alert(`Erro: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  const remove = async () => {
    if (!confirm('Remover sua preferência de vida?')) return
    setSaving(true)
    try {
      await fetch(`${API_BASE}/api/preferences/spiritual`, { method: 'DELETE', headers })
      setPref(null)
      setSelectedReligion('')
      setCustomLabel('')
      setOpen(false)
    } catch (e: any) {
      alert(`Erro: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  // Modo resumo (botão no header)
  const currentLabel = pref?.religion_label || pref?.custom_label || null
  const currentEmoji = pref?.religion_emoji || '🙏'

  return (
    <div className="relative" ref={popoverRef}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex flex-col items-center sm:flex-row sm:gap-2 px-2 py-1 sm:px-3 sm:py-1.5 rounded-lg transition-colors hover:bg-[#1a1a1a]"
        style={{
          background: pref ? 'rgba(245, 158, 11, 0.15)' : 'rgba(245, 158, 11, 0.05)',
          color: pref ? '#FCD34D' : '#D97706',
          border: pref
            ? '1px solid rgba(245, 158, 11, 0.4)'
            : '1px solid rgba(245, 158, 11, 0.2)',
        }}
        title={pref ? `Orientação: ${currentLabel}. Clique pra mudar.` : 'Escolher orientação de vida'}
        aria-label={pref ? `Orientação selecionada: ${currentLabel}` : 'Selecionar preferência de vida'}
        aria-pressed={!!pref}
      >
        <div className="flex items-center gap-1.5">
          <span style={{ fontSize: '14px', lineHeight: 1 }}>{currentEmoji}</span>
          <span className="text-xs font-medium hidden sm:inline">
            {currentLabel?.split(' ')[0] || 'Orientação de vida'}
          </span>
        </div>
        <span className="text-[9px] sm:text-[10px] opacity-70 leading-tight mt-0.5 sm:mt-0 max-w-[100px] sm:max-w-none text-center sm:text-left">
          {pref ? currentLabel?.slice(0, 36) || 'selecionada' : 'Escolha o que te representa'}
        </span>
      </button>

      {open && (
        <div
          className="absolute left-0 top-full mt-2 z-50 rounded-xl shadow-2xl"
          style={{
            background: '#0A0A0A',
            border: '1px solid rgba(252, 211, 77, 0.3)',
            minWidth: '300px',
            maxWidth: '380px',
            maxHeight: '70vh',
            overflow: 'auto',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div className="px-4 py-3 border-b border-ayria-border flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Church size={16} className="text-amber-300" />
              <span className="text-sm font-semibold text-ayria-text">Sua orientação de vida</span>
            </div>
            <button onClick={() => setOpen(false)} className="text-ayria-muted hover:text-ayria-text">
              <X size={16} />
            </button>
          </div>

          {loading ? (
            <div className="px-4 py-6 text-center text-xs text-ayria-muted">Carregando...</div>
          ) : (
            <div className="px-3 py-3 space-y-2">
              <p className="text-xs text-ayria-muted px-1">
                Escolha o que te representa. Como prefere que eu trate esses temas?
              </p>

              {/* Lista de religiões */}
              <div className="grid grid-cols-1 gap-1 max-h-56 overflow-auto pr-1">
                {options.map((opt) => {
                  const isSelected = selectedReligion === opt.value
                  return (
                    <button
                      key={opt.value}
                      onClick={() => setSelectedReligion(opt.value)}
                      className={`flex items-center gap-2 px-3 py-2 rounded-lg text-left text-sm transition-colors ${
                        isSelected
                          ? 'bg-amber-500/15 ring-1 ring-amber-400/50 text-ayria-text'
                          : 'hover:bg-white/5 text-ayria-text'
                      }`}
                    >
                      <span style={{ fontSize: '14px', width: '20px', textAlign: 'center' }}>{opt.emoji}</span>
                      <span className="flex-1">{opt.label}</span>
                      {isSelected && <Check size={14} className="text-amber-400" />}
                    </button>
                  )
                })}
              </div>

              {/* Detalhes extras (só se selecionou "outro" — pra descrever) */}
              {selectedReligion === 'outro' && (
                <div className="pt-2 border-t border-ayria-border">
                  <label className="block text-xs text-ayria-muted mb-1">
                    Descreva sua orientação *
                  </label>
                  <input
                    value={customLabel}
                    onChange={(e) => setCustomLabel(e.target.value)}
                    placeholder="Ex: Xamanismo, Taoísmo..."
                    className="w-full px-3 py-2 rounded-lg text-sm bg-black/40 text-ayria-text border border-ayria-border focus:outline-none focus:border-amber-400/60"
                  />
                </div>
              )}

              {/* Footer com botões */}
              <div className="flex gap-2 pt-2 border-t border-ayria-border">
                {pref && (
                  <button
                    onClick={remove}
                    disabled={saving}
                    className="flex items-center gap-1 px-3 py-2 rounded-lg text-xs text-red-400 hover:bg-red-500/10 transition-colors disabled:opacity-50"
                  >
                    <Trash2 size={12} />
                    Remover
                  </button>
                )}
                <div className="flex-1" />
                <button
                  onClick={save}
                  disabled={!selectedReligion || saving}
                  className="flex items-center gap-1 px-4 py-2 rounded-lg text-xs font-semibold text-white disabled:opacity-50"
                  style={{
                    background: selectedReligion
                      ? 'linear-gradient(135deg, #F59E0B, #D97706)'
                      : '#374151',
                  }}
                >
                  <Plus size={12} />
                  {saving ? 'Salvando...' : pref ? 'Atualizar' : 'Salvar'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
