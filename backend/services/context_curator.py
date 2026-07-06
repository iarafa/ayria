"""
AYRIA - Context Curator

Extrai APENAS o que importa pra cada intent. Não serializa JSON, não trunca.
Reutilizável por Supervisor, Chat e qualquer outro módulo que precise de
contexto cirúrgico do usuário.

Estratégia: dados já estão persistidos no banco (índices GIN em user_profiles).
Extrair só os campos relevantes pra tarefa atual.
"""
from __future__ import annotations
from typing import Optional
import logging

import models

logger = logging.getLogger(__name__)


# ============================================================
# INTENTS
# ============================================================
INTENT_NONE = "none"
INTENT_GERAL = "geral"
INTENT_TAROT = "tarot"
INTENT_ASTROLOGIA = "astrologia"
INTENT_NUMEROLOGIA = "numerologia"
INTENT_ESPIRITUAL = "espiritual"
INTENT_RELACIONAMENTOS = "relacionamentos"
INTENT_CARREIRA = "carreira"
INTENT_LUTO = "luto"
INTENT_SEGURANCA = "seguranca_crise"


_KEYWORDS_INTENT = {
    INTENT_TAROT: ["tarot", "carta", "puxa uma carta", "tirar carta",
                   "jogar tarot", "cruz", "spread", "baralho"],
    INTENT_ASTROLOGIA: ["signo", "astrolog", "mapa astral", "ascendente",
                        "sol em", "lua em", "horóscopo", "planeta"],
    INTENT_NUMEROLOGIA: ["numerologia", "número da sorte", "caminho de vida",
                         "número de expressão", "número da alma",
                         "ano pessoal", "meu número"],
    INTENT_ESPIRITUAL: ["deus", "jesus", "bíblia", "oração", "fé",
                        "religião", "espiritual", "espírita", "budismo"],
}


def detect_intent(user_message: str) -> str:
    """Heurística simples — detecta intent da mensagem."""
    msg = user_message.lower()
    for intent, keywords in _KEYWORDS_INTENT.items():
        if any(kw in msg for kw in keywords):
            return intent
    return INTENT_GERAL


# ============================================================
# CURADORIA
# ============================================================
def curate_profile(
    user: models.User,
    profile: Optional[models.UserProfile],
    intent: str = INTENT_GERAL,
) -> str:
    """String curta com APENAS o que importa pra intent.

    Args:
        intent: INTENT_* (padrão: INTENT_GERAL)
    """
    attrs = (profile.attributes if profile else {}) or {}
    parts = []

    # Nome + objetivo + foco (quase sempre relevantes)
    nome = attrs.get("nome_completo", "") or attrs.get("nome", "")
    if nome:
        parts.append(f"Usuário: {nome}")

    objetivo = (attrs.get("objetivo_principal", "") or "").strip()
    if objetivo:
        parts.append(f"Objetivo: {objetivo[:200]}")

    foco_list = attrs.get("principais_foco", []) or []
    if foco_list:
        parts.append(f"Foco: {', '.join(foco_list[:3])}")

    # Específico por intent
    if intent == INTENT_NUMEROLOGIA and user.numerology_data:
        num = user.numerology_data
        ano = num.get("ano_pessoal", {}).get("numero", "?")
        caminho = num.get("caminho_vida", {}).get("numero", "?")
        alma = num.get("alma", {}).get("numero", "?")
        expr = num.get("expressao", {}).get("numero", "?")
        parts.append(
            f"Numerologia: ano {ano}, caminho {caminho}, "
            f"alma {alma}, expressão {expr}"
        )

    elif intent == INTENT_ASTROLOGIA and user.astrology_data:
        ast = user.astrology_data
        sol = ast.get("sol", {}).get("signo_pt", "?")
        asc = ast.get("ascendente", {}).get("signo_pt", "?")
        lua = ast.get("lua", {}).get("signo_pt", "?")
        parts.append(f"Astrologia: sol {sol}, lua {lua}, asc {asc}")
        sol_dir = ast.get("diretrizes_sol", {})
        if sol_dir:
            tom = (sol_dir.get("tom", "") or "")[:60]
            cuidado = (sol_dir.get("cuidado", "") or "")[:80]
            if tom or cuidado:
                parts.append(f"Tom sol: {tom}. Cuidado: {cuidado}")

    if not parts:
        return "(perfil mínimo)"

    return " | ".join(parts)


def curate_spiritual_preference(sp: Optional[models.SpiritualPreference]) -> str:
    """String curta com preferência espiritual (se houver e ativa)."""
    if not sp or not sp.is_active:
        return ""
    label = sp.custom_label or sp.religion or ""
    tags = ", ".join(sp.custom_tags) if sp.custom_tags else ""
    notes = (sp.notes or "")[:150]
    parts = [f"Religião/visao: {label}"]
    if tags:
        parts.append(f"tags: {tags}")
    if notes:
        parts.append(f"nota: {notes}")
    return " | ".join(parts)


# Curadores de essência (pros Supervisor — bem compactos)
def curate_numerology_essence(user: models.User) -> str:
    num = user.numerology_data or {}
    if not num:
        return ""
    return (
        f"ano {num.get('ano_pessoal', {}).get('numero','?')}, "
        f"caminho {num.get('caminho_vida', {}).get('numero','?')}, "
        f"alma {num.get('alma', {}).get('numero','?')}"
    )


def curate_astrology_directives(user: models.User) -> str:
    """Diretrizes canônicas (resumo oficial do autor) — supervisor/chat."""
    ast = user.astrology_data or {}
    if not ast:
        return ""
    sol = ast.get("diretrizes_sol", {}) or {}
    asc = ast.get("diretrizes_ascendente", {}) or {}
    sol_tom = (sol.get("tom", "") or "")[:60]
    sol_cuidado = (sol.get("cuidado", "") or "")[:80]
    asc_tom = (asc.get("tom", "") or "")[:60]
    asc_cuidado = (asc.get("cuidado", "") or "")[:80]
    return (
        f"Sol ({sol_tom}): {sol_cuidado}. "
        f"Ascendente ({asc_tom}): {asc_cuidado}"
    )
