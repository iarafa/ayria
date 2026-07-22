/**
 * AYRIA - ListWithControls
 *
 * Wrapper genérico: pega qualquer lista visual (children) e adiciona por cima:
 * - 🔍 Busca por texto (filtra por campos searchable)
 * - 📄 Paginação (prev/next + primeira/última)
 * - 📊 Escolha de quantidade por página (10/25/50/100)
 * - 📋 Contador "mostrando X-Y de N"
 *
 * Mantém o visual original dos children (não força tabela).
 *
 * Props:
 * - data: any[] — fonte de dados pra filtro
 * - children: (item: T) => ReactNode — render de cada item
 * - searchableKeys?: string[] — quais campos usar pra busca (default: ['email', 'full_name', 'name'])
 * - searchFields?: (item) => string — função custom de extração de texto pra busca
 * - pageSize?: number (default 25)
 * - emptyMessage?: string
 * - searchPlaceholder?: string
 * - itemName?: string (ex: 'usuário', 'admin', 'documento')
 * - idKey?: string (default 'id')
 *
 * Uso:
 * ```tsx
 * <ListWithControls data={users} itemName="usuário">
 *   {(u) => <UserRow user={u} />}
 * </ListWithControls>
 * ```
 */
import { useState, useMemo } from 'react'
import { Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export interface ListWithControlsProps<T> {
  data: T[]
  children: (item: T) => React.ReactNode
  searchableKeys?: string[]
  searchFields?: (item: T) => string
  pageSize?: number
  emptyMessage?: string
  searchPlaceholder?: string
  itemName?: string
  idKey?: string
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

export function ListWithControls<T extends Record<string, any>>({
  data,
  children,
  searchableKeys = ['email', 'full_name', 'name', 'title'],
  searchFields,
  pageSize: initialPageSize = 25,
  emptyMessage = 'Nenhum registro encontrado',
  searchPlaceholder = 'Buscar...',
  itemName = 'registro',
  idKey = 'id',
}: ListWithControlsProps<T>) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // 1) Filtra por busca
  const filtered = useMemo(() => {
    if (!search.trim()) return data
    const q = search.toLowerCase()
    return data.filter((row) => {
      if (searchFields) {
        return searchFields(row).toLowerCase().includes(q)
      }
      return searchableKeys.some((key) => {
        const v = row[key]
        return v != null && String(v).toLowerCase().includes(q)
      })
    })
  }, [data, search, searchableKeys, searchFields])

  // 2) Paginação
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const startIdx = (safePage - 1) * pageSize
  const pageData = filtered.slice(startIdx, startIdx + pageSize)

  return (
    <div>
      {/* Toolbar: busca + escolha de page size + contador */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <div className="relative flex-1 min-w-[200px] max-w-md">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ayria-muted" />
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-3 py-2 rounded-lg text-sm"
            style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
          />
        </div>
        <div className="flex items-center gap-3 text-xs text-ayria-muted">
          <span>
            {filtered.length === data.length
              ? `${filtered.length} ${itemName}${filtered.length !== 1 ? 's' : ''}`
              : `${filtered.length} de ${data.length} ${itemName}${data.length !== 1 ? 's' : ''}`}
          </span>
          <div className="flex items-center gap-1">
            <span>Por página:</span>
            <select
              value={pageSize}
              onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1) }}
              className="px-2 py-1 rounded text-xs"
              style={{ background: '#0A0A1A', border: '1px solid #2a2a3e', color: '#fff' }}
            >
              {PAGE_SIZE_OPTIONS.map((n) => (
                <option key={n} value={n}>{n}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Lista filtrada/paginada */}
      <div className="space-y-2">
        {pageData.length === 0 ? (
          <div className="text-center text-ayria-muted py-8">{emptyMessage}</div>
        ) : (
          pageData.map((item) => <div key={item[idKey]}>{children(item)}</div>)
        )}
      </div>

      {/* Paginação */}
      {filtered.length > 0 && (
        <div className="flex flex-wrap items-center justify-between gap-2 mt-3 text-xs text-ayria-muted">
          <span>
            Mostrando {startIdx + 1}-{Math.min(startIdx + pageSize, filtered.length)} de {filtered.length}
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={safePage === 1}
              className="p-1 rounded disabled:opacity-30 hover:bg-[#1a1a2e]"
              title="Primeira página"
            >
              <ChevronsLeft size={14} />
            </button>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={safePage === 1}
              className="p-1 rounded disabled:opacity-30 hover:bg-[#1a1a2e]"
              title="Anterior"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="px-3">
              Página <strong className="text-ayria-text">{safePage}</strong> de {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={safePage === totalPages}
              className="p-1 rounded disabled:opacity-30 hover:bg-[#1a1a2e]"
              title="Próxima"
            >
              <ChevronRight size={14} />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={safePage === totalPages}
              className="p-1 rounded disabled:opacity-30 hover:bg-[#1a1a2e]"
              title="Última página"
            >
              <ChevronsRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
