"""
Gera mapa arquitetural dos prompts do sistema AYRIA.

Usado pelo chat de co-edição (/api/admin/prompt/chat) pra que a IA
entenda que cada .md NÃO é independente — eles têm relacionamentos:

1. Constituição Base — sempre carregada, define tom/idioma/segurança base
2. Módulos temáticos — carregados sob demanda pelo classificador
3. Supervisor — roda paralelo, detecta risco, injeta crise
4. RAG (Qdrant) — indexa tudo, permite busca cross-file

Quando a IA sugerir nova versão de um MD, ela precisa saber QUEM
mais depende daquele arquivo e O QUE ele referencia em outros.
"""

from pathlib import Path
from typing import Dict, List

from services.prompt_selector import (
    PROMPTS_DIR,
    AVAILABLE_MODULES,
    KEYWORDS,
    load_constitution,
)

# Mapeamento estático de categorias/dependências (curado pelo admin)
# Mostra PROPOSITO de cada arquivo e sua relação com o todo
CATEGORY_PURPOSE = {
    "base": "Constituição — define identidade, tom, segurança base, idioma pt-BR. SEMPRE carregada.",
    "admin": "Permissões e contexto quando o usuário é admin.",
    "astrologia": "Tema astrológico: signos, mapa astral, planetas, casas.",
    "carreira": "Tema profissional: trabalho, demissão, promoção, transição.",
    "luto": "Tema perda/óbito/mudança significativa — usa tom acolhedor.",
    "memoria": "Recupera e usa memórias do usuário.",
    "numerologia": "Tema numerológico: caminho de vida, expressão, ano pessoal.",
    "onboarding": "Perguntas pra construir perfil do usuário.",
    "psicanalise": "Tema psicanalítico: inconsciente, sonhos, mecanismos de defesa.",
    "psicologia": "Tema psicológico: ansiedade, depressão, terapia, TDAH, TOC.",
    "relacionamentos": "Tema amor, parceria, família, conflito interpessoal.",
    "religiao": "Tema espiritualidade, fé, sentido — respeitoso e não proselitista.",
    "tarot": "Tema tarot: tiragem, interpretação de cartas.",
    "visao_mundo": "Tema filosofia, propósito, ética, visão de mundo.",
}


def get_module_keywords(key: str) -> List[str]:
    """Retorna lista de keywords que ativam este módulo."""
    raw = KEYWORDS.get(key, [])
    kws = []
    for r in raw[:8]:
        # KEYWORDS armazena strings (regex raw); remove \b
        clean = r.replace("\b", "").strip()
        if clean and clean not in kws:
            kws.append(clean)
    return kws[:5]


def get_related_modules(key: str) -> List[str]:
    """Quais módulos são frequentemente ativados JUNTOS com este."""
    # Mapeamento heurístico simples — baseado em co-ocorrência
    RELATED = {
        "luto": ["psicologia", "relacionamentos"],
        "psicanalise": ["psicologia", "luto"],
        "psicologia": ["psicanalise", "luto", "relacionamentos"],
        "relacionamentos": ["psicologia", "carreira"],
        "carreira": ["relacionamentos", "visao_mundo"],
        "numerologia": ["astrologia", "tarot"],
        "astrologia": ["numerologia", "tarot"],
        "tarot": ["numerologia", "astrologia"],
        "onboarding": [],
        "memoria": ["psicologia", "relacionamentos"],
        "religiao": ["visao_mundo", "luto"],
        "visao_mundo": ["religiao", "carreira"],
        "admin": [],
    }
    return RELATED.get(key, [])


def build_architecture_map(current_key: str) -> str:
    """
    Gera o MAPA ARQUITETURAL completo do sistema, com foco no arquivo current_key.

    Usado como contexto no system_prompt do chat de co-edição.
    """
    # Determina categoria
    if current_key == "constituicao_base":
        categoria_atual = "base"
        scope = "raiz: prompts/prompt_base.md"
    elif current_key == "supervisor_seguranca_crise":
        categoria_atual = "supervisor"
        scope = "prompts/supervisor/seguranca_crise.md (SEPARADO dos módulos — sempre roda em paralelo)"
    elif current_key.startswith("modulo_"):
        categoria_atual = current_key.replace("modulo_", "", 1)
        scope = f"prompts/prompt_{categoria_atual}.md"
    else:
        categoria_atual = current_key
        scope = current_key

    lines = []
    lines.append("🗺️  MAPA ARQUITETURAL DO SISTEMA AYRIA")
    lines.append("=" * 60)
    lines.append("")
    lines.append("📌 Arquivo que você está editando agora:")
    lines.append(f"   • key: `{current_key}`")
    lines.append(f"   • path: `{scope}`")
    lines.append(f"   • propósito: {CATEGORY_PURPOSE.get(categoria_atual, 'módulo temático carregado sob demanda')}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("🧠 AS 4 CAMADAS DO SISTEMA (ordem de prioridade)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("1️⃣  CONSTITUIÇÃO BASE (`prompt_base.md`)")
    lines.append("   • SEMPRE carregada em TODA conversa, independente do tema")
    lines.append("   • Define: identidade 'AYRIA', tom acolhedor/sábio, regras de segurança,")
    lines.append("     IDIOMA pt-BR (regra absoluta), formato de resposta")
    lines.append("   • ⛔ NÃO duplicar regras que já existem aqui nos módulos!")
    lines.append("")
    lines.append("2️⃣  MÓDULOS TEMÁTICOS (sob demanda)")
    lines.append("   • Carregados pelo classificador quando keywords batem")
    if categoria_atual not in ("base", "supervisor") and categoria_atual != "admin":
        lines.append(f"   • ⭐ VOCÊ ESTÁ EM: `{categoria_atual}`")
        lines.append(f"   • Keywords que ativam este módulo: {', '.join(get_module_keywords(categoria_atual)) or '(nenhuma)'}")
        related = get_related_modules(categoria_atual)
        if related:
            lines.append(f"   • 🔗 Módulos frequentemente co-ativados: {', '.join(related)}")
        else:
            lines.append(f"   • 🔗 Módulo independente (sem co-ativação frequente)")
    lines.append(f"   • 📋 Total de módulos ativos: {len(AVAILABLE_MODULES)}")
    lines.append("   • Lista completa:")
    for m in AVAILABLE_MODULES:
        marker = " ⭐" if m == categoria_atual else ""
        lines.append(f"     - {m}: {CATEGORY_PURPOSE.get(m, '?')}{marker}")
    lines.append("")
    lines.append("3️⃣  SUPERVISOR DE SEGURANÇA (`supervisor/seguranca_crise.md`)")
    lines.append("   • Roda em PARALELO a cada mensagem do usuário")
    lines.append("   • Detecta risco em 3 níveis: N1 (suicídio/homicídio), N2 (crimes/violência), N3 (vícios)")
    lines.append("   • Se detecta, INJETA o módulo de crise automaticamente")
    lines.append("   • Define tom de acolhimento em momentos sensíveis")
    lines.append("")
    lines.append("4️⃣  RAG (Qdrant)")
    lines.append("   • Indexa TUDO dos .md em chunks semânticos")
    lines.append("   • Permite que a Ayria busque cross-file quando relevante")
    lines.append("   • Coleção `conhecimento_geral`")
    lines.append("")

    lines.append("=" * 60)
    lines.append("⚠️  REGRAS CRÍTICAS DE CO-EDIÇÃO")
    lines.append("=" * 60)
    lines.append("")
    lines.append("ANTES de propor uma nova versão do arquivo atual, VOCÊ DEVE:")
    lines.append("")
    lines.append("1. 🔍 CHECAR DUPLICAÇÃO")
    lines.append("   • 'ser empática' já tá na Constituição? NÃO reescreva no módulo.")
    lines.append("   • 'respeitar autonomia' já existe em outro lugar? NÃO duplique.")
    lines.append("   • Se a regra MELHOR se encaixa em outra camada,")
    lines.append("     AVISE ao admin onde colocar em vez de duplicar.")
    lines.append("")
    lines.append("2. ⚖️  CHECAR CONTRADIÇÃO")
    lines.append("   • Sua proposta contradiz a Constituição? NÃO prossiga.")
    lines.append("   • Sua proposta contradiz outro módulo? AVISE.")
    lines.append("")
    lines.append("3. 🎯 CHECAR ESCOPO")
    lines.append("   • Keywords deste módulo não estouraram pra outro tema?")
    lines.append("   • A IA não vai ativar ESTE módulo quando o usuário perguntar X?")
    lines.append("")
    lines.append("4. 🌐 CHECAR IDIOMA")
    lines.append("   • SEMPRE pt-BR. Nada de chinês/japonês/coreano.")
    lines.append("   • Mantenha acentos e expressões naturais do Brasil.")
    lines.append("")
    lines.append("QUANDO DETECTAR PROBLEMA → responda no INÍCIO da análise:")
    lines.append("   ⚠️ 'ATENÇÃO: a regra X já existe em [Constituição|outro módulo].")
    lines.append("      Sugiro colocar em [local correto] em vez de duplicar.'")
    lines.append("")

    return "\n".join(lines)


def get_summary_of_siblings(current_key: str, max_chars: int = 2000) -> str:
    """
    Retorna sumário curto (1-2 parágrafos) dos arquivos mais relacionados
    a `current_key`, pra dar contexto sem inflar o prompt.

    Fallback caso `current_key` seja a Constituição ou supervisor — aí
    mostra o que ESTES mencionam.
    """
    related_keys = []
    if current_key == "constituicao_base":
        # Constituição referencia todos os módulos → mostra 1-2 mais referenciados
        related_keys = AVAILABLE_MODULES[:3]
    elif current_key.startswith("modulo_"):
        short = current_key.replace("modulo_", "", 1)
        related_keys = ["base"] + get_related_modules(short)
    elif current_key == "supervisor_seguranca_crise":
        related_keys = ["base", "psicologia", "luto"]

    related_keys = [k for k in related_keys if k]

    if not related_keys:
        return ""

    out = ["📎 SUMÁRIO DOS ARQUIVOS RELACIONADOS:\n"]
    for k in related_keys:
        if k == "base":
            content = load_constitution()
            path = "prompt_base.md"
        else:
            md_path = PROMPTS_DIR / f"prompt_{k}.md"
            content = md_path.read_text(encoding="utf-8") if md_path.exists() else ""
            path = f"prompt_{k}.md"

        if not content:
            continue

        # Primeiro parágrafo ou primeiros 200 chars
        snippet = content.strip().split("\n\n")[0] if "\n\n" in content else content[:200]
        if len(snippet) > 250:
            snippet = snippet[:250] + "..."
        out.append(f"--- {path} ---")
        out.append(snippet)
        out.append("")

    text = "\n".join(out)
    if len(text) > max_chars:
        text = text[:max_chars] + "\n... (truncado pra economizar tokens)"
    return text
