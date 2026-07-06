"""
AYRIA - Sanitizador de respostas da IA.

PROBLEMA: MiniMax M3 às vezes mistura caracteres CJK (chinês/japonês/coreano)
no meio de respostas em PT-BR. Isso é inaceitável pra um produto BR.

SOLUÇÃO: detectar caracteres não-latinos (CJK, hiragana, katakana, hangul,
símbolos ideográficos) e REMOVER ou SUBSTITUIR antes de mandar pro user.

Aplica-se em TODA resposta da IA — defesa em camadas:
1. Pós-geração: regex remove caracteres não-permitidos
2. Se removeu muito (>0 chars): log + metadata flag pra auditoria
3. System prompt reforça PT-BR puro (defesa upstream)
"""
import re
import logging
import unicodedata

logger = logging.getLogger(__name__)

# Ranges Unicode que NÃO devem aparecer em resposta em PT-BR:
# - Hiragana:     U+3040 - U+309F
# - Katakana:     U+30A0 - U+30FF
# - CJK Unified:  U+4E00 - U+9FFF (chinês/japonês core)
# - CJK Ext A:    U+3400 - U+4DBF
# - CJK Symbols:  U+3000 - U+303F (espaços e pontuação CJK)
# - Hangul:       U+AC00 - U+D7AF (coreano)
# - CJK Compat:   U+F900 - U+FAFF
# - Fullwidth:    U+FF00 - U+FFEF (pontuação full-width asiática)
_CJK_RE = re.compile(
    "["
    "\u3040-\u309F"   # Hiragana
    "\u30A0-\u30FF"   # Katakana
    "\u3400-\u4DBF"   # CJK Extension A
    "\u4E00-\u9FFF"   # CJK Unified Ideographs
    "\u3000-\u303F"   # CJK Symbols and Punctuation
    "\uAC00-\uD7AF"   # Hangul Syllables
    "\uF900-\uFAFF"   # CJK Compatibility Ideographs
    "\uFF00-\uFFEF"   # Halfwidth and Fullwidth Forms
    "\u31F0-\u31FF"   # Katakana Phonetic Extensions
    "]"
)

# Caracteres latinos permitidos (incluindo acentos pt-BR):
# Letras latinas com diacríticos, números, pontuação comum, espaços, emoji, símbolos
# Não rejeitamos: ç á à â ã é ê í ó ô õ ú ü ñ ... (latin-1 + latin extended)


def _is_cjk_or_unwanted(ch: str) -> bool:
    """Retorna True se o caractere é CJK/asiático e deve ser removido."""
    if _CJK_RE.match(ch):
        return True
    return False


def sanitize_response(text: str, *, source: str = "ai_response") -> tuple[str, dict]:
    """
    Sanitiza resposta da IA removendo caracteres CJK/asiáticos.

    Args:
        text: texto gerado pela IA
        source: origem (pra log)

    Returns:
        (texto_limpo, stats) onde stats = {
            'sanitized': bool,
            'removed_count': int,
            'removed_chars': list[str]  # amostra
            'removed_categories': list[str]
        }

    CRÍTICO: este filtro é a ÚLTIMA linha de defesa. Nunca confie 100%
    no system prompt pra evitar mistura de idiomas — sempre sanitize.
    """
    if not text:
        return text, {"sanitized": False, "removed_count": 0, "removed_chars": [], "removed_categories": []}

    removed_chars: list[str] = []
    removed_categories: set[str] = set()

    cleaned_chars = []
    for ch in text:
        if _is_cjk_or_unwanted(ch):
            # Substitui por espaço pra evitar juntar palavras
            cleaned_chars.append(" ")
            removed_chars.append(ch)
            try:
                cat = unicodedata.name(ch, "UNKNOWN")
                if "CJK" in cat or "HIRAGANA" in cat or "KATAKANA" in cat or "HANGUL" in cat:
                    removed_categories.add(cat.split()[0])
            except Exception:
                pass
        else:
            cleaned_chars.append(ch)

    cleaned = "".join(cleaned_chars)

    # Limpa múltiplos espaços que ficaram da remoção
    cleaned = re.sub(r" {2,}", " ", cleaned)
    # Limpa espaço antes de pontuação
    cleaned = re.sub(r" +([.,;:!?])", r"\1", cleaned)

    stats = {
        "sanitized": len(removed_chars) > 0,
        "removed_count": len(removed_chars),
        "removed_chars_sample": removed_chars[:20],  # máximo 20 pra metadata
        "removed_categories": sorted(removed_categories),
        "source": source,
    }

    if removed_chars:
        logger.warning(
            f"🧹 SANITIZE [{source}]: removidos {len(removed_chars)} caracteres CJK. "
            f"Sample: {removed_chars[:10]!r}. Categorias: {removed_categories}"
        )

    return cleaned, stats


def quick_check(text: str) -> bool:
    """
    Check rápido: tem caracteres CJK?
    Útil pra decidir se precisa sanitizar (evita regex em todo byte).
    """
    if not text:
        return False
    return bool(_CJK_RE.search(text))