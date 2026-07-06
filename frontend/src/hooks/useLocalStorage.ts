/**
 * useLocalStorage — Hook genérico para persistir estado em localStorage.
 *
 * Uso:
 *   const [value, setValue] = useLocalStorage('meu-key', true)
 *   setValue(false) // persiste automaticamente
 *
 * - Sincroniza entre abas/janelas via evento 'storage'
 * - Trata JSON parse/serialize automaticamente
 * - Falha silenciosa se localStorage não disponível (SSR, modo anônimo)
 */
import { useEffect, useState } from 'react'

export function useLocalStorage<T>(
  key: string,
  initialValue: T
): [T, (value: T | ((val: T) => T)) => void] {
  // Inicializa lendo do localStorage (se disponível)
  const [storedValue, setStoredValue] = useState<T>(() => {
    if (typeof window === 'undefined') return initialValue
    try {
      const item = window.localStorage.getItem(key)
      return item !== null ? (JSON.parse(item) as T) : initialValue
    } catch (error) {
      console.warn(`useLocalStorage: erro ao ler ${key}`, error)
      return initialValue
    }
  })

  // Wrapper que persiste quando muda
  const setValue = (value: T | ((val: T) => T)) => {
    try {
      const valueToStore =
        value instanceof Function ? value(storedValue) : value
      setStoredValue(valueToStore)
      if (typeof window !== 'undefined') {
        window.localStorage.setItem(key, JSON.stringify(valueToStore))
      }
    } catch (error) {
      console.warn(`useLocalStorage: erro ao gravar ${key}`, error)
    }
  }

  // Sincroniza entre abas/janelas
  useEffect(() => {
    if (typeof window === 'undefined') return
    const handleStorage = (e: StorageEvent) => {
      if (e.key === key && e.newValue !== null) {
        try {
          setStoredValue(JSON.parse(e.newValue))
        } catch {
          // ignore
        }
      }
    }
    window.addEventListener('storage', handleStorage)
    return () => window.removeEventListener('storage', handleStorage)
  }, [key])

  return [storedValue, setValue]
}
