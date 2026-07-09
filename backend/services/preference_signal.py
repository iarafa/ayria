"""
AYRIA - Preference Signal Detector (08/07/2026)

Detecta quando a mensagem do user contém um pedido de mudança de TOM/PREFERÊNCIA
e classifica o tipo. É a "orelha" que faltava: usuário fala "seja mais meiga"
e o sistema regenera a sub-alma dele automaticamente (auto-merge → active direto).

Plano §5: Detecção de preference signal.

Abordagem MVP: regex/keywords em pt-BR (cobre 95% dos casos).
Quando quiser mais sofisticado (classificador IA leve), é só evoluir essa função.
"""
import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ============================================================
# PADRÕES (case-insensitive, com/sem acentos)
# ============================================================
# Estrutura: cada padrão retorna (tipo, payload) quando faz match.

# Tom (mais/menos adjective) — match robusto: "ser mais X", "mais X (por favor)"
_TOM_MAIS = re.compile(
    r"\bmais\s+([a-záéíóúçãõêôûà]+(?:\s+(?:e|ou|de|da|do|com)\s+[a-záéíóúçãõêôû]+){0,3})(?:\s|,|\.|!|\?|$)",
    re.IGNORECASE,
)
_TOM_MENOS = re.compile(
    r"\bmenos\s+([a-záéíóúçãõêôûà]+(?:\s+(?:e|ou|de|da|do|com)\s+[a-záéíóúçãõêôû]+){0,3})(?:\s|,|\.|!|\?|$)",
    re.IGNORECASE,
)

# Tom negativo direto: palavras isoladas "groça/grosseira/seca/ríspida/agressiva/duro"
_TOM_NEGATIVO = re.compile(
    r"\b(gros[sc][aeiou]|grosseir[ao]|r[áa]spid[ao]|sec[ao]|fria?|agressiv[ao]|direct[aá]?|duro|chata|chato|d[eé]sagrad[aá]vel)\b",
    re.IGNORECASE,
)

# Apelido: "me chama de X" / "pode me chamar de X" / "chamar X"
_APELIDO = re.compile(
    r"(?:me\s+)?(?:pode\s+)?(?:me\s+)?cham[aeo]r?(?:[- ]me)?\s+(?:de|por|como)\s+([A-Za-záéíóúçãõêôûÀ-ú]+)",
    re.IGNORECASE,
)
_APELIDO_SIMPLES = re.compile(
    r"(?:^|\s)cham[ae]me?\s+([A-Za-záéíóúçãõêôûÀ-ú]+)\b",
    re.IGNORECASE,
)

# Estilo: resposta curta/longa, sem/com emojis, sem disclaimer
_ESTILO_TAMANHO = re.compile(
    r"\b(curtas?|longas?|pequenas?|grandes?|breves?|objetivas?|resumidas?)\b",
    re.IGNORECASE,
)
_ESTILO_EMOJI = re.compile(
    r"\b(?:sem|com|menos|mais)\s+emoj[ie]s?\b",
    re.IGNORECASE,
)
_ESTILO_DISCLAIMER = re.compile(
    r"\b(?:sem|menos)\s+disclaimers?\b",
    re.IGNORECASE,
)

# Evitar: "não fala de X" / "evita X"
_EVITAR = re.compile(
    r"(?:n[ãa]o\s+fal[ae]\s+(?:de|sobre)\s+|evit[ae]r?\s+)([a-záéíóúçãõêôûà]+(?:\s+(?:de|da|do|e|ou)\s+[a-záéíóúçãõêôûà]+){0,3})",
    re.IGNORECASE,
)

# Frases de queixa: "está sendo muito groça", "tá sendo agressiva"
_FRASE_QUEIXA = re.compile(
    r"\b(?:est[áa]|t[áa]|estava|tava|fic[ao]|foi)\s+(?:sendo\s+)?(?:muito\s+|demais\s+|meio\s+)?(gros[sc][aeiou]|grosseir[ao]|r[áa]spid[ao]|sec[ao]|fria?|agressiv[ao]|duro|chata|chato|d[eé]sagrad[aá]vel)",
    re.IGNORECASE,
)


# ============================================================
# DETECTOR
# ============================================================
def detect_preference_signal(user_message: str) -> Optional[Dict[str, Any]]:
    """Detecta se a mensagem contém preference signal.

    Retorna dict com {type, key, value, raw_phrase} se detectou, ou None.
    SEMPRE retorna só 1 signal por mensagem (o primeiro que casar).
    Decisão consciente: pegar 1 evita "spam" de regeneração.
    """
    if not user_message or len(user_message) > 2000:
        return None

    msg = user_message.strip()

    # 0) Frases de queixa ("está sendo muito groça") → tom negativo direto
    m = _FRASE_QUEIXA.search(msg)
    if m:
        return {
            "type": "tom",
            "direction": "menos",
            "key": "tom",
            "value": m.group(1).lower(),
            "raw_phrase": m.group(0).strip(),
        }

    # 1) Apelido (mais forte — nomeia o user)
    m = _APELIDO.search(msg)
    if m:
        nickname = m.group(1).strip().lower()
        if len(nickname) >= 2 and not nickname.endswith((" de", " para", " por", " com")):
            return {
                "type": "apelido",
                "key": "apelido",
                "value": nickname,
                "raw_phrase": m.group(0).strip(),
            }

    # Apelido simples fallback ("chame X")
    m = _APELIDO_SIMPLES.search(msg)
    if m:
        nickname = m.group(1).strip().lower()
        if len(nickname) >= 2:
            return {
                "type": "apelido",
                "key": "apelido",
                "value": nickname,
                "raw_phrase": m.group(0).strip(),
            }

    # 2) Tom positivo (ser mais meiga)
    m = _TOM_MAIS.search(msg)
    if m:
        tone = m.group(1).strip().lower()
        if tone not in {"em", "de", "com", "para", "por", "a", "o", "e", "que", "um", "uma", "mais"}:
            return {
                "type": "tom",
                "direction": "mais",
                "key": "tom",
                "value": tone,
                "raw_phrase": m.group(0).strip(),
            }

    # 3) Tom negativo (ser menos X)
    m = _TOM_MENOS.search(msg)
    if m:
        tone = m.group(1).strip().lower()
        if tone not in {"em", "de", "com", "para", "por", "a", "o", "e", "que", "um", "uma", "mais"}:
            return {
                "type": "tom",
                "direction": "menos",
                "key": "tom",
                "value": tone,
                "raw_phrase": m.group(0).strip(),
            }

    # 4) Tom negativo isolado ("groça")
    m = _TOM_NEGATIVO.search(msg)
    if m:
        return {
            "type": "tom",
            "direction": "menos",
            "key": "tom",
            "value": m.group(1).lower(),
            "raw_phrase": m.group(0).strip(),
        }

    # 5) Tamanho de resposta (se tiver palavra de comando junto)
    if any(cmd in msg.lower() for cmd in ["resposta", "frase", "mensagem", "texto", "responder", "responda"]):
        m = _ESTILO_TAMANHO.search(msg)
        if m:
            size = m.group(1).lower()
            if "curta" in size or "pequena" in size or "breve" in size or "objetiva" in size or "resumida" in size:
                return {"type": "estilo", "key": "tamanho", "value": "curta", "raw_phrase": m.group(0).strip()}
            if "longa" in size or "grande" in size:
                return {"type": "estilo", "key": "tamanho", "value": "longa", "raw_phrase": m.group(0).strip()}

    # 6) Emojis
    m = _ESTILO_EMOJI.search(msg)
    if m:
        phrase = m.group(0).lower()
        if "sem" in phrase or "menos" in phrase:
            return {"type": "estilo", "key": "emoji", "value": "sem", "raw_phrase": phrase}
        return {"type": "estilo", "key": "emoji", "value": "com", "raw_phrase": phrase}

    # 7) Disclaimers
    if _ESTILO_DISCLAIMER.search(msg):
        return {"type": "estilo", "key": "disclaimer", "value": "sem", "raw_phrase": "sem disclaimer"}

    # 8) Evitar temas
    m = _EVITAR.search(msg)
    if m:
        topic = m.group(1).strip().lower()
        if len(topic) >= 3:
            return {
                "type": "evitar",
                "key": "evitar",
                "value": topic,
                "raw_phrase": m.group(0).strip(),
            }

    return None


def describe_signal(signal: Dict[str, Any]) -> str:
    """Devolve uma descrição humana do sinal (pra UI/log)."""
    t = signal.get("type", "")
    if t == "apelido":
        return f"Apelido preferido → '{signal['value']}'"
    if t == "tom":
        d = signal.get("direction", "")
        return f"Tom: {d} {signal['value']}"
    if t == "estilo":
        return f"Estilo ({signal['key']}): {signal['value']}"
    if t == "evitar":
        return f"Evitar: {signal['value']}"
    return f"Sinal: {signal}"


# ============================================================
# Auto-teste rápido (roda só se invocado diretamente)
# ============================================================
if __name__ == "__main__":
    tests = [
        "Vc vao me tratar mais carinhosamente ?",
        "Vc esta sendo muito groca e direta comigo",
        "me chama de Peron",
        "pode me chamar de Rafa",
        "seja mais meiga",
        "seja mais direta",
        "respostas mais curtas",
        "sem emojis por favor",
        "sem disclaimer",
        "nao fala sobre política",
        "oi tudo bem?",  # deve dar None
    ]
    for t in tests:
        s = detect_preference_signal(t)
        print(f"{'✅' if s else '➖'} {t[:60]:<60} → {describe_signal(s) if s else '—'}")
