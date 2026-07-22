/**
 * AYRIA - DataTable
 *
 * Tabela reutilizável com:
 * - 🔍 Busca em tempo real (filtra por colunas searchable)
 * - 📄 Paginação (prev/next + números)
 * - 📊 Escolha de quantidade por página (10 / 25 / 50 / 100)
 * - 📋 Total de registros
 * - 🎨 Visual consistente com o tema dark AYRIA
 * - 📱 Responsivo
 *
 * Props:
 * - data: T[] — array de dados
 * - columns: { key, label, searchable?, render?, width? }[] — definição das colunas
 *   - searchable: se true, esta coluna entra no filtro de busca
 *   - render: função opcional (row) => ReactNode — custom rendering (ex: avatar)
 * - pageSize?: number (default 25)
 * - emptyMessage?: string
 * - searchPlaceholder?: string
 * - idKey?: string (default 'id') — chave única pra key={...}
 *
 * Uso:
 * ```tsx
 * <DataTable
 *   data={users}
 *   columns={[
 *     { key: 'email', label: 'Email', searchable: true, width: '40%' },
 *     { key: 'full_name', label: 'Nome', searchable: true },
 *     { key: 'role', label: 'Role', render: (u) => <Badge>{u.role}</Badge> },
 *   ]}
 * />
 * ```
 */
import { useState, useMemo } from 'react'
import { Search, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react'

export interface DataTableColumn<T> {
  key: string
  label: string
  searchable?: boolean
  render?: (row: T) => React.ReactNode
  width?: string  // ex: '40%', '200px'
  align?: 'left' | 'center' | 'right'
}

export interface DataTableProps<T> {
  data: T[]
  columns: DataTableColumn<T>[]
  pageSize?: number
  emptyMessage?: string
  searchPlaceholder?: string
  idKey?: string
}

const PAGE_SIZE_OPTIONS = [10, 25, 50, 100]

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  pageSize: initialPageSize = 25,
  emptyMessage = 'Nenhum registro encontrado',
  searchPlaceholder = 'Buscar...',
  idKey = 'id',
}: DataTableProps<T>) {
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(initialPageSize)

  // 1) Filtra por busca (todas as colunas searchable)
  const filtered = useMemo(() => {
    if (!search.trim()) return data
    const q = search.toLowerCase()
    return data.filter((row) =>
      columns
        .filter((c) => c.searchable)
        .some((c) => {
          const v = row[c.key]
          return v != null && String(v).toLowerCase().includes(q)
        })
    )
  }, [data, search, columns])

  // 2) Paginação
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize))
  const safePage = Math.min(page, totalPages)
  const startIdx = (safePage - 1) * pageSize
  const pageData = filtered.slice(startIdx, startIdx + pageSize)

  // Reset page quando filtro muda
  if (page !== safePage && safePage > 0) {
    setTimeout(() => setPage(safePage), 0)
  }

  return (
    <div className="w-full">
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
              ? `${filtered.length} registros`
              : `${filtered.length} de ${data.length}`}
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

      {/* Tabela */}
      <div className="overflow-x-auto rounded-xl" style={{ border: '1px solid #2a2a3e' }}>
        <table className="w-full text-sm">
          <thead style={{ background: '#0F0F1F' }}>
            <tr>
              {columns.map((c) => (
                <th
                  key={c.key}
                  className="px-4 py-3 text-left text-xs font-medium text-ayria-muted uppercase tracking-wider"
                  style={{ width: c.width, textAlign: c.align || 'left' }}
                >
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 py-12 text-center text-ayria-muted">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              pageData.map((row) => (
                <tr
                  key={row[idKey]}
                  style={{ borderTop: '1px solid #2a2a3e' }}
                  className="hover:bg-[#1a1a2e] transition-colors"
                >
                  {columns.map((c) => (
                    <td
                      key={c.key}
                      className="px-4 py-3 text-ayria-text"
                      style={{ textAlign: c.align || 'left' }}
                    >
                      {c.render ? c.render(row) : row[c.key] ?? '—'}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
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
