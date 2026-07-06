import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './index.css'
import { checkCacheBust } from './lib/cacheBuster'

// ⚠️ CACHE ZERO: roda ANTES de tudo
// Se a versão do build mudou, limpa localStorage e dá reload
// Isso garante que tokens/dados velhos não persistem
checkCacheBust()

// HashRouter: usado pra funcionar quando o app é servido em subpath (ex: /ayria/)
// Como o nginx serve Ayria em https://agente.tecia.app/ayria/ e o React Router
// usa paths absolutos, o basename quebraria rotas internas (# funciona em qualquer path)
ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>,
)
