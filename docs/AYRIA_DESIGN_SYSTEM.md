# AYRIA — Design System & Brand Identity

## 1. Logo

### Conceito: "O Elo da Consciência"
O logo da AYRIA combina três elementos simbólicos:
- **A letra "A"** de Ayria, fundida com o símbolo do **Infinito** — representando os ciclos da vida e o crescimento contínuo.
- **Um Ponto/Núcleo Central** com brilho sutil (glow) — representando o indivíduo, o autoconhecimento e a consciência.
- **Estilo:** Traços finos e futuristas, elegantes, sobre fundo escuro.

### Arquivo Gerado
- `ayria_logo.png` — Logo principal gerado por IA (1024x1024px)
- Fundo: Preto profundo `#050505`
- Cores do símbolo: Indigo `#6366F1` + Roxo `#A855F7` + Prata `#F8FAFC`

### Regras de Uso do Logo
- ✅ Usar sempre sobre fundo escuro (`#050505` ou `#111111`)
- ✅ Manter proporção original (não distorcer)
- ❌ Não usar sobre fundos claros
- ❌ Não alterar as cores do logo
- ❌ Não adicionar sombras externas ou efeitos extras

---

## 2. Paleta de Cores

### Cores Principais (Tailwind CSS)

| Função                        | Hex       | Tailwind Class         | Descrição                                              |
|-------------------------------|-----------|------------------------|--------------------------------------------------------|
| Background Principal          | `#050505` | `bg-[#050505]`         | Preto profundo — foco total na conversa                |
| Background Secundário (Cards) | `#111111` | `bg-[#111111]`         | Cinza quase preto — profundidade e camadas             |
| Primary (Destaque)            | `#6366F1` | `bg-indigo-500`        | Indigo — confiança, sabedoria, tecnologia              |
| Accent (Ação)                 | `#A855F7` | `bg-purple-500`        | Roxo vibrante — botões de ação, estados ativos         |
| Texto Principal               | `#F8FAFC` | `text-slate-50`        | Off-white — leitura confortável, sem cansaço visual    |
| Texto Secundário              | `#94A3B8` | `text-slate-400`       | Cinza azulado — metadados, datas, legendas             |
| Sucesso / Confirmação         | `#10B981` | `text-emerald-500`     | Verde esmeralda — cálculos concluídos, estados OK      |
| Erro / Alerta                 | `#EF4444` | `text-red-500`         | Vermelho — erros, alertas críticos                     |
| Borda Sutil                   | `#1E1E2E` | `border-[#1E1E2E]`     | Borda quase invisível para separar seções              |

### Gradientes Recomendados

```css
/* Gradiente de destaque — botões principais */
background: linear-gradient(135deg, #6366F1, #A855F7);

/* Gradiente de fundo sutil — cards especiais */
background: linear-gradient(180deg, #111111, #050505);

/* Glow do logo / ícone central */
box-shadow: 0 0 24px rgba(99, 102, 241, 0.4);
```

---

## 3. Tipografia

### Fonte Principal: Inter
- **Fonte:** [Inter](https://fonts.google.com/specimen/Inter) (Google Fonts)
- **Por quê:** Mesma fonte do ChatGPT, Linear e Vercel. Moderna, legível e transmite seriedade.

### Import no HTML / Tailwind
```html
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
```

```css
font-family: 'Inter', sans-serif;
```

### Hierarquia Tipográfica

| Elemento            | Tamanho | Peso   | Cor              |
|---------------------|---------|--------|------------------|
| Título Principal    | 32px    | 700    | `#F8FAFC`        |
| Subtítulo / H2      | 24px    | 600    | `#F8FAFC`        |
| Corpo de Texto      | 16px    | 400    | `#F8FAFC`        |
| Texto Secundário    | 14px    | 400    | `#94A3B8`        |
| Labels / Metadados  | 12px    | 500    | `#94A3B8`        |
| Código / Técnico    | 14px    | 400    | `#A855F7` (mono) |

---

## 4. Layout Geral

### Estrutura da Interface (Chat Principal)

```
┌─────────────────────────────────────────────────────────┐
│  SIDEBAR (260px)          │  ÁREA PRINCIPAL             │
│  ─────────────────        │  ─────────────────────────  │
│  [Logo AYRIA]             │  [Header: Nome do Chat]     │
│                           │                             │
│  [+ Nova Conversa]        │  ┌─────────────────────┐   │
│                           │  │  Mensagem Ayria      │   │
│  ── Conversas ──          │  └─────────────────────┘   │
│  > Chat de hoje           │                             │
│  > Onboarding             │  ┌─────────────────────┐   │
│  > Sessão anterior        │  │  Mensagem Usuário   │   │
│                           │  └─────────────────────┘   │
│  ── ──────────── ──       │                             │
│  [Perfil do Usuário]      │  [Input de Mensagem    📤]  │
└─────────────────────────────────────────────────────────┘
```

### Dimensões
- **Sidebar:** `260px` fixo, fundo `#111111`
- **Área Principal:** `flex-1`, fundo `#050505`
- **Input de Mensagem:** `max-w-3xl`, centralizado, com `rounded-2xl` e borda `#1E1E2E`
- **Balões de Chat:** `max-w-[75%]`

---

## 5. Componentes de Chat

### Mensagem da AYRIA
```css
background: #111111;
border: 1px solid rgba(99, 102, 241, 0.2);
border-radius: 16px;
padding: 16px;
color: #F8FAFC;
```

### Mensagem do Usuário
```css
background: linear-gradient(135deg, #6366F1, #A855F7);
border-radius: 16px;
padding: 16px;
color: #FFFFFF;
align-self: flex-end;
```

### Botão Principal (CTA)
```css
background: linear-gradient(135deg, #6366F1, #A855F7);
border-radius: 12px;
padding: 12px 24px;
font-weight: 600;
color: #FFFFFF;
transition: opacity 0.2s;
```

### Input de Mensagem
```css
background: #111111;
border: 1px solid #1E1E2E;
border-radius: 16px;
padding: 16px;
color: #F8FAFC;
font-family: 'Inter', sans-serif;
```

---

## 6. Efeitos Visuais

### Glassmorphism (Sidebar / Header)
```css
background: rgba(17, 17, 17, 0.8);
backdrop-filter: blur(12px);
border-bottom: 1px solid rgba(99, 102, 241, 0.1);
```

### Glow nos Elementos Ativos
```css
box-shadow: 0 0 20px rgba(99, 102, 241, 0.3);
```

### Animação de Loading (Typing Indicator)
- Três pontos pulsando em `#6366F1`
- Animação: `pulse` com delay escalonado (0ms, 150ms, 300ms)

---

## 7. Área Admin

### Diferenciação Visual
- **Fundo:** `#0A0A1A` (azul muito escuro) para diferenciar da área do usuário
- **Accent Admin:** `#F59E0B` (Amber) para ações administrativas críticas
- **Badge Admin:** Tag `ADMIN` em `#F59E0B` no header

---

## 8. Responsividade

| Breakpoint | Comportamento                                      |
|------------|----------------------------------------------------|
| Desktop    | Sidebar visível + área principal                   |
| Tablet     | Sidebar colapsável (ícones apenas)                 |
| Mobile     | Sidebar oculta, acessível via menu hambúrguer      |

---

## 9. Tailwind Config (tailwind.config.js)

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        ayria: {
          bg: '#050505',
          card: '#111111',
          border: '#1E1E2E',
          primary: '#6366F1',
          accent: '#A855F7',
          text: '#F8FAFC',
          muted: '#94A3B8',
          success: '#10B981',
          error: '#EF4444',
          admin: '#F59E0B',
        }
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      }
    }
  }
}
```

---

## 10. Resumo Visual (Quick Reference)

```
AYRIA Design System — Quick Reference
======================================
Logo:        Indigo + Roxo + Prata sobre fundo preto
Background:  #050505 (principal) / #111111 (cards)
Primary:     #6366F1 (Indigo)
Accent:      #A855F7 (Roxo)
Texto:       #F8FAFC (principal) / #94A3B8 (secundário)
Sucesso:     #10B981 (Esmeralda)
Fonte:       Inter (Google Fonts)
Bordas:      rounded-xl (12px) / rounded-2xl (16px)
Efeito:      Glassmorphism + Glow Indigo
```
