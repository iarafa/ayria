"""
AYRIA - Supervisor Service
Classificação de risco de mensagens do usuário.

3 níveis:
- NORMAL: conversa saudável
- ATENCAO: sinais moderados de sofrimento (silencioso, persistente)
- URGENCIA: sinais críticos (autolesão, suicídio, violência)
"""
import json
import logging
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.ai_service import ai_service
from database import settings
import models

logger = logging.getLogger(__name__)

PROMPT_TEMPLATE = """Você é o SUPERVISOR de bem-estar da Ayria, uma IA de autoconhecimento.
Sua ÚNICA função é classificar a mensagem abaixo quanto ao NÍVEL DE RISCO psicossocial do usuário.

## CLASSIFICAÇÃO (escolha UMA)

- NORMAL (score 0.0-0.3): conversa saudável, dúvidas existenciais leves, curiosidade
  Exemplos: "Como funciona signo?", "Tenho dormido pouco", "Quero entender meu mapa"

- ATENCAO (score 0.4-0.7): sinais de sofrimento emocional, ideação passiva, padrão preocupante
  Exemplos: "Tô sozinho", "Não aguento mais", "Nada faz sentido", autocrítica severa

- URGENCIA (score 0.8-1.0): ideação suicida ativa, autolesão, violência contra si ou terceiros
  Exemplos: "Quero morrer", "Vou me machucar", "Tenho um plano", ameaça a outros

## SINAIS PARA DETECTAR (liste em "signals")

URGENCIA: "quero morrer", "vou me matar", "me suicidar", "tirar minha vida", "acabar com tudo",
"me machucar", "me cortar", "vou sumir", "não vou estar aqui", plano, método, data
violência: "vou matar", "vou fazer ele sofrer", "quero vingança", "vou me explodir"

ATENCAO: solidão persistente, "ninguém se importa", "sou um fardo", "não sou bom o suficiente",
"fracasso", "inútil", insônia crônica, ansiedade, "não consigo mais", desesperança, choro frequente

NORMAL: perguntas gerais, reflexões leves, agradecimentos, dúvidas práticas

## CONTEXTO DO USUÁRIO

- Plano: {plan_name}
- Perfil (onboarding): {onboarding}
- Numerologia (resumo): {numerology}
- Astrologia (diretrizes): {astrology}
- Histórico recente: {history}
- Mensagens recentes do chat:
{recent_messages}

## MENSAGEM ATUAL

"{message_content}"

## FORMATO DE RESPOSTA (JSON ESTRITO, sem markdown)

{{
  "level": "NORMAL" | "ATENCAO" | "URGENCIA",
  "score": 0.0-1.0,
  "reason": "explicação curta (max 200 chars)",
  "signals": ["sinal1", "sinal2"],
  "recommended_action": "ação sugerida (ex: 'Oferecer escuta ativa', 'Recomendar CVV 188', 'Notificar admin')"
}}
"""


class SupervisorService:
    """Classifica mensagens de usuários em níveis de risco."""

    # ============================================================
# REGEX DE PRÉ-CHECAGEM (instantâneo, sem gastar IA)
# Cobre 3 níveis de risco:
#  - NIVEL 1 (URGÊNCIA): suicídio, autolesão, homicídio
#  - NIVEL 2 (ATENÇÃO): crimes, violência doméstica, ameaças
#  - NIVEL 3 (ATENÇÃO): vícios graves, compulsões
# ============================================================
    CRITICAL_PATTERNS_NIVEL_1 = [
        # suicídio / autolesão
        r"\b(quero|vou|vamos)\s+(me\s+)?(matar|morrer|suicidar)\b",
        r"\btirar\s+(a|minha)\s+vida\b",
        r"\bme\s+(matar|machucar|cortar|sangrar)\b",
        r"\bacabar\s+com\s+tudo\b",
        r"\bnão\s+vou\s+(estar|viver)\s+(mais|aqui)\b",
        r"\b(plano|plano\s+de)\s+(morte|suicídio|matar)\b",
        r"\bvou\s+(sumir|desaparecer)\b",
        r"\bexplodir\s+(tudo|a\s+casa|a\s+vida)\b",
        r"\bseria\s+melhor\s+se\s+eu\s+não\s+existisse\b",
        # homicídio
        r"\bvou\s+(matar|fazer\s+ele\s+sofrer)\s+(alguém|ele|ela)\b",
        r"\bestou\s+pensando\s+em\s+matar\s+(ele|ela|alguém)\b",
    ]

    CRITICAL_PATTERNS_NIVEL_2 = [
        # crimes / violência
        r"\bvou\s+(roubar|tráfico|traficar|agredir|estuprar)\b",
        r"\bviolência\s+doméstica\b",
        r"\bmeu\s+parceiro\s+me\s+bate\b",
        r"\bvou\s+denunciar\s+(falso|falsamente)\b",
        r"\bconfesso\s+que\s+(matei|roubei|agredi)\b",
    ]

    CRITICAL_PATTERNS_NIVEL_3 = [
        # vícios graves
        r"\bvício\s+em\s+(apostas|jogo|cassino|bingo)\b",
        r"\bjogatina\b",
        r"\b(anorexia|bulimia)\b",
        r"\btranstorno\s+alimentar\b",
        r"\b(overdose|overdosei)\b",
        r"\bálcool\s+(demais|em\s+excesso)\b",
        r"\bdrogas\s+(demais|em\s+excesso)\b",
    ]

    CRITICAL_PATTERNS = (
        CRITICAL_PATTERNS_NIVEL_1
        + CRITICAL_PATTERNS_NIVEL_2
        + CRITICAL_PATTERNS_NIVEL_3
    )

    # ============================================================
    # KEYWORDS CARREGADAS DO .md (curadas pelo admin)
    # Categoria — cada uma tem seu nível. O batch usa pra decidir
    # SE chama IA. Pré-check do chat usa pra URGÊNCIA (N1+N2 = bloqueia).
    # ============================================================
    KEYWORDS_FILE = "keywords_crise.md"
    # Carregado lazy (cache após primeira leitura — admin pode editar sem restart)
    _keywords_cache: Optional[Dict[str, list]] = None
    _keywords_mtime: Optional[float] = None

    @classmethod
    def _load_keywords_from_md(cls) -> Dict[str, list]:
        """Carrega keywords categorizadas do MD.

        Formato do arquivo .md:
            ## N1 — ...        # Categoria com nome começando com "N1", "N2", "N3", "ATENCAO"
            - "frase"           # 1 keyword por linha começando com "-"
            - 'frase'           # aceita aspas simples ou duplas

        Returns:
            {
                "N1": [regex compilado, ...],
                "N2": [regex compilado, ...],
                "N3": [regex compilado, ...],
                "ATENCAO": [regex compilado, ...],
                "_source": path do arquivo,
                "_mtime": float mtime,
            }
        """
        from pathlib import Path
        p = Path(__file__).parent.parent / "prompts" / "supervisor" / cls.KEYWORDS_FILE
        if not p.exists():
            logger.warning(f"⚠️ Keywords file não encontrado: {p}")
            return {"_source": str(p), "_mtime": 0}

        mtime = p.stat().st_mtime
        # Cache: se mtime mudou, recarrega
        if cls._keywords_mtime == mtime and cls._keywords_cache:
            return cls._keywords_cache

        # Parse
        result: Dict[str, list] = {"_source": str(p), "_mtime": mtime}
        for cat in ("N1", "N2", "N3", "ATENCAO"):
            result.setdefault(cat, [])
        current_cat = None
        for raw_line in p.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            # Comentário de linha única: começa com "#" mas NÃO "##"
            if line.startswith("#") and not line.startswith("##"):
                continue
            # Categoria: linha começando com "##"
            if line.startswith("##"):
                head = line.lstrip("#").strip()
                head_upper = head.upper()
                # NEGATIVE = palavras/frases que ANULAM um match positivo
                # Ex: "morreu de rir", "morto de cansaco" — falsos positivos comuns
                if head_upper.startswith("NEGATIVE") or head_upper.startswith("NEGATIVAS"):
                    current_cat = "NEGATIVE"
                    result.setdefault("NEGATIVE", [])
                    continue
                # SLIGHT = verbos soltos (matar/morrer/matando) que viram risco
                # só em contexto. Tratados como ATENCAO mas anuláveis por NEGATIVE.
                if head_upper.startswith("SLIGHT"):
                    current_cat = "SLIGHT"
                    result.setdefault("SLIGHT", [])
                    continue
                for cat in ("N1", "N2", "N3", "ATENCAO"):
                    if head_upper.startswith(cat + " ") or head_upper == cat:
                        current_cat = cat
                        result.setdefault(cat, [])
                        break
                continue
            # Keyword: linha começando com "-" ou "'" ou '"'
            if line.startswith("-") or line.startswith('"') or line.startswith("'"):
                # Remove comentário inline (# ...) que veio grudado na linha
                txt_full = line.lstrip("- ").strip()
                if "#" in txt_full:
                    # Corta tudo a partir do primeiro # que esteja FORA de aspas
                    # Simplificado: split no primeiro # (não usamos # dentro de regex aqui)
                    txt_full = txt_full.split("#", 1)[0].strip()
                txt = txt_full.strip('"').strip("'")
                if not txt:
                    continue
                if current_cat and current_cat in ("N1", "N2", "N3", "ATENCAO", "NEGATIVE", "SLIGHT"):
                    try:
                        pattern = r"\b" + re.escape(txt) + r"\b"
                        result[current_cat].append(re.compile(pattern, re.IGNORECASE))
                    except re.error as e:
                        logger.warning(f"  Regex inválida '{txt}': {e}")

        logger.info(
            f"📂 Keywords carregadas: N1={len(result.get('N1', []))} "
            f"N2={len(result.get('N2', []))} "
            f"N3={len(result.get('N3', []))} "
            f"ATENCAO={len(result.get('ATENCAO', []))}"
        )
        cls._keywords_cache = result
        cls._keywords_mtime = mtime
        return result

    @classmethod
    def check_keywords(cls, content: str) -> Tuple[Optional[str], Optional[int], list]:
        """Verifica keywords contra o conteúdo. Retorna (level, sublevel, matched).

        Returns:
            ("URGENCIA", 1, ["quero morrer"]) — bateu com N1
            ("ATENCAO", 2, ["vou roubar"]) — bateu com N2
            ("ATENCAO", 3, ["vício em apostas"]) — bateu com N3
            ("ATENCAO", None, ["não aguento mais"]) — bateu com ATENCAO
            (None, None, []) — nada bateu (chamar IA ou não é decisão do caller)

        Ordem de prioridade: N1 > N2 > N3 > ATENCAO.
        Quando match positivo (N1-N3/ATENCAO) acontece E também bate um NEGATIVE
        (falso positivo conhecido: "morreu de rir"), o match é ANULADO (N1/N2/N3
        explícitos NUNCA são anulados — se tem "quero morrer" na msg, é risco real
        independente do resto; mas match em ATENCAO puro é anulável).
        """
        kw = cls._load_keywords_from_md()
        content_lower = content.lower()

        # N1 (crítico — suicídio/homicídio) — NUNCA anulado por NEGATIVE
        # Se uma msg tem AMBOS "quero morrer" E "morreu de rir", é real.
        for pat in kw.get("N1", []):
            if pat.search(content):
                return "URGENCIA", 1, [pat.pattern]
        # N2 (crítico — crimes/violência) — NUNCA anulado
        for pat in kw.get("N2", []):
            if pat.search(content):
                return "URGENCIA", 2, [pat.pattern]
        # N3 (atenção — vícios) — NUNCA anulado
        for pat in kw.get("N3", []):
            if pat.search(content):
                return "ATENCAO", 3, [pat.pattern]
        # ATENCAO (sinais moderados) — pode ser anulado se bater NEGATIVE
        atencao_match = None
        for pat in kw.get("ATENCAO", []):
            if pat.search(content):
                atencao_match = ("ATENCAO", None, [pat.pattern])
                break
        # SLIGHT (verbos soltos: "matar", "morrer", "morrendo")
        # Dependem de contexto — tratados como ATENCAO anulável por NEGATIVE.
        # Cobre falsos positivos: "morreu de rir", "matou a fome".
        # Mas conteúdo explícito ("quero morrer") está em N1 e nunca é anulado.
        if not atencao_match:
            for pat in kw.get("SLIGHT", []):
                if pat.search(content):
                    atencao_match = ("ATENCAO", None, [pat.pattern])
                    break

        if atencao_match:
            negative_matches = []
            for pat in kw.get("NEGATIVE", []):
                if pat.search(content):
                    negative_matches.append(pat.pattern)
            if negative_matches:
                logger.info(
                    f"[check_keywords] ATENCAO anulada por NEGATIVE: "
                    f"match={atencao_match[2]}, negative={negative_matches}"
                )
                return None, None, []  # falso positivo anulado
            return atencao_match

        return None, None, []

    @classmethod
    def should_analyze_with_ia(cls, content: str) -> bool:
        """Decide se vale chamar IA pra classificar essa msg.

        Princípio: SE nenhum sinal de risco → marca NORMAL direto (sem IA).
        SE tem QUALQUER sinal de risco → chama IA pra confirmar.
        """
        level, _, _ = cls.check_keywords(content)
        return level is not None

    @classmethod
    def quick_classify_from_keywords(cls, content: str) -> Tuple[str, float, list, Optional[int]]:
        """Wrapper que mantém compat com _quick_check.

        Returns: (level, score, signals, sublevel)
        """
        level, sublevel, matched = cls.check_keywords(content)
        if level == "URGENCIA":
            return level, 0.92, matched, sublevel
        elif level == "ATENCAO":
            return level, 0.65, matched, sublevel
        return None, 0.0, [], None

    # Marcadores de modelo usado (pra diferenciar regex-only vs IA)
    # True = análise realmente veio da IA (não só pré-check regex)
    IA_MODEL_MARKERS = ("minimax", "gpt-", "claude", "gemini", "mistral", "llama")

    @classmethod
    def _is_ia_model(cls, model_used: Optional[str]) -> bool:
        if not model_used:
            return False
        m = model_used.lower()
        return any(marker in m for marker in cls.IA_MODEL_MARKERS)

    def __init__(self):
        self.critical_re = re.compile("|".join(self.CRITICAL_PATTERNS), re.IGNORECASE)
        self.nivel1_re = re.compile("|".join(self.CRITICAL_PATTERNS_NIVEL_1), re.IGNORECASE)
        self.nivel2_re = re.compile("|".join(self.CRITICAL_PATTERNS_NIVEL_2), re.IGNORECASE)
        self.nivel3_re = re.compile("|".join(self.CRITICAL_PATTERNS_NIVEL_3), re.IGNORECASE)
        logger.info("✅ SupervisorService inicializado (3 níveis de regex)")

    async def get_recent_cache(self, db: AsyncSession, user_id: str, max_age_seconds: int = 3600):
        """Busca análise recente do user (cache). Retorna None se não houver recente.

        Usado pra evitar chamada IA repetida quando o user já teve análise recente
        do mesmo nível. MAX age default: 1h.
        """
        from datetime import datetime, timedelta
        from sqlalchemy import select

        cutoff = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        res = await db.execute(
            select(models.SupervisorAnalysis)
            .where(
                models.SupervisorAnalysis.user_id == user_id,
                models.SupervisorAnalysis.created_at >= cutoff,
            )
            .order_by(models.SupervisorAnalysis.created_at.desc())
            .limit(1)
        )
        cached = res.scalar_one_or_none()
        if cached:
            cache_age = (datetime.utcnow() - cached.created_at).total_seconds()
            logger.info(
                f"⚡ Supervisor cache HIT: user={user_id} level={cached.level} "
                f"idade={cache_age:.0f}s (pula IA)"
            )
        return cached

    async def analyze_sync_with_cache(
        self,
        db: AsyncSession,
        message: models.Message,
        chat: models.Chat,
        user: models.User,
        timeout_seconds: float = 4.0,
        cache_max_age_seconds: int = 3600,
    ) -> models.SupervisorAnalysis:
        """Versão SYNC com cache + timeout — roda ANTES do chat principal.

        Fluxo:
        1. Pré-check regex (instantâneo, 0 IA)
        2. Cache: análise recente do mesmo user? usa ela (sem IA)
        3. IA supervisor com TIMEOUT — se estourar, fallback seguro
        4. Resultado salvo é o mesmo que analyze_message

        Diferença: timeboxed, com cache agressivo, retorna sempre análise salva
        (mesmo em erro/fallback — preferível a travar chat).
        """
        import asyncio

        # 1) Pré-check regex primeiro — se URGÊNCIA, vai pelo caminho rápido
        quick_level, quick_score, quick_signals, quick_sublevel = self._quick_check(message.content)

        # 2) Cache: análise recente?
        try:
            cached = await self.get_recent_cache(db, str(user.id), cache_max_age_seconds)
            if cached:
                # Reutiliza análise cacheada como base
                new_analysis = models.SupervisorAnalysis(
                    message_id=message.id,
                    user_id=user.id,
                    chat_id=chat.id,
                    level=cached.level,
                    risk_sublevel=cached.risk_sublevel,
                    score=cached.score,
                    reason=f"Cache: {cached.reason}"[:500],
                    signals=cached.signals or [],
                    recommended_action=cached.recommended_action or "",
                    model_used="cache-recent",
                    analysis_duration_ms=0,
                )
                db.add(new_analysis)
                await db.commit()
                await db.refresh(new_analysis)
                return new_analysis
        except Exception as e:
            logger.warning(f"Cache check falhou (ignorando): {e}")

        # 3) Pré-check URGÊNCIA: vai direto, sem gastar IA
        if quick_level == "URGENCIA":
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="URGENCIA",
                risk_sublevel=quick_sublevel,
                score=min(0.99, max(0.85, quick_score)),
                reason="Padrão crítico detectado (regex pré-checagem)",
                signals=quick_signals,
                recommended_action="🚨 NÍVEL 1 (vida): notificar admin + CVV (188)",
                model_used="regex-pre-check",
                analysis_duration_ms=0,
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            logger.warning(f"🚨 URGÊNCIA detectada (regex sync) — user={user.email} msg={message.id}")
            return analysis

        # 4) IA com TIMEOUT
        try:
            analysis = await asyncio.wait_for(
                self.analyze_message(db, message, chat, user),
                timeout=timeout_seconds,
            )
            return analysis
        except asyncio.TimeoutError:
            logger.warning(
                f"⏱️ Supervisor IA TIMEOUT ({timeout_seconds}s) — usando fallback seguro. "
                f"user={user.email}"
            )
            # Fallback: análise "AI indisponível" sem bloquear chat
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="ATENCAO",
                score=0.3,
                risk_sublevel=quick_sublevel,
                reason=f"⏱️ Supervisor IA excedeu timeout ({timeout_seconds}s). "
                       f"Pré-check regex: {quick_level or 'NORMAL'}",
                signals=quick_signals or [],
                recommended_action="Análise IA indisponível (timeout). Revisão recomendada.",
                model_used="timeout-fallback",
                analysis_duration_ms=int(timeout_seconds * 1000),
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return analysis
        except Exception as e:
            logger.error(f"❌ Supervisor sync falhou: {e}", exc_info=True)
            # Erro inesperado — fallback seguro
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="ATENCAO",
                score=0.3,
                risk_sublevel=quick_sublevel,
                reason=f"Erro no supervisor (sync): {str(e)[:200]}",
                signals=quick_signals or [],
                recommended_action="Análise IA falhou. Revisão recomendada.",
                model_used="error-sync-fallback",
                analysis_duration_ms=0,
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return analysis

    async def analyze_message(
        self,
        db: AsyncSession,
        message: models.Message,
        chat: models.Chat,
        user: models.User,
    ) -> models.SupervisorAnalysis:
        """
        Analisa uma mensagem do usuário. Retorna o registro SupervisorAnalysis salvo.
        NÃO BLOQUEIA o caller — usado via BackgroundTasks.
        """
        start = time.time()

        # Pré-checagem: regex crítica → URGÊNCIA direta (sem gastar IA)
        quick_level, quick_score, quick_signals, quick_sublevel = self._quick_check(message.content)

        if quick_level == "URGENCIA":
            # URGÊNCIA crítica — não precisa gastar IA
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="URGENCIA",
                risk_sublevel=quick_sublevel,
                score=min(0.99, max(0.85, quick_score)),
                reason="Padrão crítico detectado (regex pré-checagem)",
                signals=quick_signals,
                recommended_action=(
                    "🚨 NÍVEL 1 (vida): notificar admin + oferecer CVV (188) + escuta ativa imediata"
                    if quick_sublevel == 1
                    else "⚠️ NÍVEL 2 (crime/violência): abordar de forma firme, recusar orientação criminosa, orientar ajuda"
                    if quick_sublevel == 2
                    else "⚠️ NÍVEL 3 (vício): acolher sem julgar, sugerir ajuda especializada"
                ),
                model_used="regex-pre-check",
                analysis_duration_ms=int((time.time() - start) * 1000),
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            logger.warning(f"🚨 URGÊNCIA detectada (regex) — user={user.email} msg={message.id}")
            return analysis

        # ATENÇÃO pré-detectada por regex (N2 crimes ou N3 vícios) — salva direto
        if quick_level == "ATENCAO":
            action_text = (
                "⚠️ NÍVEL 2 (crime/violência): abordar de forma firme, recusar orientação criminosa, orientar ajuda"
                if quick_sublevel == 2
                else "⚠️ NÍVEL 3 (vício): acolher sem julgar, sugerir ajuda especializada"
            )
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="ATENCAO",
                risk_sublevel=quick_sublevel,
                score=quick_score,
                reason="Padrão de risco moderado detectado (regex pré-checagem)",
                signals=quick_signals,
                recommended_action=action_text,
                model_used="regex-pre-check",
                analysis_duration_ms=int((time.time() - start) * 1000),
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            logger.warning(f"⚠️ ATENÇÃO Nível {quick_sublevel} detectada — user={user.email} msg={message.id}")
            return analysis

        # Análise com IA
        try:
            context = await self._build_context(db, user, chat, message)

            # Carrega prompt de supervisor (custom do banco OU arquivo)
            supervisor_module = await self._load_supervisor_module(db)

            prompt = PROMPT_TEMPLATE.format(
                plan_name=context["plan_name"],
                onboarding=context["onboarding"],        # já é string curada
                numerology=context["numerology"],        # já é string curada
                astrology=context["astrology"],          # já é string curada
                history=context.get("history", "(sem histórico)"),
                recent_messages=context["recent_messages"],
                message_content=message.content[:2000],
            )

            # Enriquece com o módulo de segurança/crise do admin (se houver)
            if supervisor_module:
                prompt += (
                    "\n\n## CRITÉRIOS OFICIAIS DE RISCO (do admin)\n\n"
                    f"{supervisor_module[:1500]}\n\n"
                    "Use esses critérios como referência para classificar a mensagem acima. "
                    "Se algum dos 3 Níveis do admin for detectado, ajuste o nível e a recommended_action conforme."
                )

            resp = await ai_service.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # ↑ era 0.1 (causava degeneração)
                max_tokens=800,   # ↑ era 500 (curto demais se IA "pensar")
            )

            result_text = (resp.choices[0].message.content or "").strip()

            if not result_text:
                # Resposta vazia — log claro + força retry/raise estruturado
                logger.warning(
                    f"⚠️ Supervisor: IA retornou resposta VAZIA. user={user.email} model={settings.AI_MODEL}"
                )
                raise ValueError("IA retornou resposta vazia")

            # Tentar extrair JSON de markdown ```json ... ```
            result_text_clean = re.sub(
                r"^```(?:json)?\s*|\s*```$", "", result_text, flags=re.MULTILINE
            ).strip()

            data = None
            parse_error = None

            # 1) parse direto
            try:
                data = json.loads(result_text_clean)
            except json.JSONDecodeError as e:
                parse_error = f"direct: {e}"

                # 2) extrair primeiro objeto {...} balanceado da string
                match = re.search(r"\{.*\}", result_text_clean, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group(0))
                    except json.JSONDecodeError as e2:
                        parse_error = f"direct+regex: {parse_error} | regex: {e2}"

            if data is None:
                # Loga a resposta raw pra diagnóstico (truncada)
                logger.error(
                    f"❌ Supervisor: não consegui parsear JSON. user={user.email} | erros={parse_error} "
                    f"| raw (first 500 chars): {result_text[:500]!r}"
                )
                raise ValueError(
                    f"IA não retornou JSON válido (após 2 tentativas): {parse_error}"
                )

            level = data.get("level", "NORMAL").upper()
            if level not in ("NORMAL", "ATENCAO", "URGENCIA"):
                level = "NORMAL"
            score = float(data.get("score", 0.0))
            score = max(0.0, min(1.0, score))

            # Boost: se regex pegou algo crítico OU se sinais contiverem "suicídio"/"morte" → URGÊNCIA
            signals = data.get("signals", [])
            ia_sublevel = None
            if any(kw in s.lower() for s in signals for kw in ["suicíd", "morte", "machuc", "homicí"]):
                level = "URGENCIA"
                score = max(score, 0.85)
                ia_sublevel = 1  # N1
            elif any(kw in s.lower() for s in signals for kw in ["violência", "crime", "ameaça"]):
                level = "ATENCAO"
                ia_sublevel = 2  # N2
                score = max(score, 0.6)
            elif any(kw in s.lower() for s in signals for kw in ["vício", "álcool", "droga", "aposta"]):
                ia_sublevel = 3  # N3
                if level == "NORMAL":
                    level = "ATENCAO"
                score = max(score, 0.55)

            # Se veio do pré-check com sublevel, usa ele
            ia_sublevel = ia_sublevel or quick_sublevel

            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level=level,
                risk_sublevel=ia_sublevel,
                score=score,
                reason=(data.get("reason", "") or "")[:500],
                recommended_action=(data.get("recommended_action", "") or "")[:500],
                signals=signals[:10],
                context_used={"plan": context["plan_name"]},
                model_used=settings.AI_MODEL,
                analysis_duration_ms=int((time.time() - start) * 1000),
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)

            logger.info(
                f"📊 Análise: level={level} score={score:.2f} "
                f"user={user.email} dur={analysis.analysis_duration_ms}ms"
            )
            return analysis

        except Exception as e:
            logger.error(f"❌ Erro na análise supervisor: {e}", exc_info=True)
            # Em caso de erro, marca ATENCAO (preferir falso positivo a falso negativo em segurança)
            analysis = models.SupervisorAnalysis(
                message_id=message.id,
                user_id=user.id,
                chat_id=chat.id,
                level="ATENCAO",
                score=0.4,
                reason=f"Falha na análise IA — marcando como ATENÇÃO por segurança: {str(e)[:200]}",
                recommended_action="Revisão manual recomendada (análise IA falhou)",
                model_used="error-fallback",
                analysis_duration_ms=int((time.time() - start) * 1000),
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return analysis

    def _quick_check(self, content: str) -> tuple:
        """
        Pré-checagem regex. Retorna (level, score, signals, sublevel).

        ✅ Lê do MD (keywords_crise.md) — hot-reload por mtime.
        """
        level, sublevel, matched = self.check_keywords(content)
        if level == "URGENCIA":
            return level, 0.95, matched, sublevel or 1
        if level == "ATENCAO":
            score = 0.75 if (sublevel == 2) else 0.65
            return level, score, matched, sublevel or 3
        return None, 0.0, [], None

    async def _load_supervisor_module(self, db: AsyncSession) -> str:
        """Carrega prompt do supervisor: banco (custom) > arquivo .md."""
        # Tenta banco
        try:
            res = await db.execute(
                select(models.AyriaPromptConfig).where(
                    models.AyriaPromptConfig.is_active == True,
                    models.AyriaPromptConfig.key == "supervisor_seguranca_crise",
                )
            )
            cfg = res.scalar_one_or_none()
            if cfg and cfg.content:
                return cfg.content
        except Exception as e:
            logger.warning(f"Falha ao ler prompt supervisor do banco: {e}")

        # Fallback arquivo
        from pathlib import Path
        f = Path(__file__).parent.parent / "prompts" / "supervisor" / "seguranca_crise.md"
        if f.exists():
            return f.read_text(encoding="utf-8")
        return ""

    async def _build_context(
        self,
        db: AsyncSession,
        user: models.User,
        chat: models.Chat,
        message: models.Message,
    ) -> Dict:
        """Monta contexto CIRÚRGICO pro supervisor — SEM truncar JSON.

        Estratégia: busca dados estruturados já persistidos no banco e extrai
        APENAS os campos relevantes pra classificar risco. Não serializa
        JSON inteiro e não trunca — usa campos curados.
        """
        # Plano
        plan_name = "Nenhum"
        if user.selected_plan_id:
            res = await db.execute(select(models.Plan).where(models.Plan.id == user.selected_plan_id))
            plan = res.scalar_one_or_none()
            if plan:
                plan_name = plan.name

        # Onboarding (já persistido em user_profiles.attributes)
        prof_res = await db.execute(
            select(models.UserProfile).where(models.UserProfile.user_id == user.id)
        )
        profile = prof_res.scalar_one_or_none()

        onboarding_min, numerology_min, astrology_min = self._extract_supervisor_context(
            user, profile
        )

        # Histórico recente do user (alertas abertos/recentes) — contexto de padrão
        history_min = await self._extract_user_history(db, user)

        # Mensagens recentes do chat — só as 3 últimas (excluindo a atual)
        msgs_res = await db.execute(
            select(models.Message)
            .where(models.Message.chat_id == chat.id)
            .order_by(models.Message.created_at.desc())
            .limit(4)  # 3 + a atual
        )
        recent = list(msgs_res.scalars().all())
        recent.reverse()
        recent_text = "\n".join(
            f"[{m.role}] {m.content[:120]}" for m in recent if m.id != message.id
        ) or "(sem histórico)"

        return {
            "plan_name": plan_name,
            "onboarding": onboarding_min,
            "numerology": numerology_min,
            "astrology": astrology_min,
            "history": history_min,
            "recent_messages": recent_text[:600],  # 3 msgs × 200 chars
        }

    def _extract_supervisor_context(self, user, profile) -> tuple:
        """Extrai APENAS o que importa pra classificar risco psicossocial.

        Busca campos curados direto do dict persistido — NÃO serializa JSON
        inteiro. Cada bloco vira 1-2 linhas curtas (≤250 chars cada).
        """
        # 1) Onboarding: foco + objetivo (já são os campos mais densos)
        attrs = (profile.attributes if profile else {}) or {}
        if attrs:
            foco_list = attrs.get('principais_foco', []) or []
            foco = ', '.join(foco_list[:3])
            objetivo = (attrs.get('objetivo_principal', '') or '').strip()[:200]
            onboarding_min = (
                f"Foco: {foco}. Objetivo: {objetivo}" if objetivo
                else f"Foco: {foco}. (sem objetivo declarado)"
            )
        else:
            onboarding_min = "(onboarding incompleto)"

        # 2) Numerologia: só números-chave pro ano corrente
        num = user.numerology_data or {}
        ano_pess = num.get('ano_pessoal', {}) or {}
        caminho = num.get('caminho_vida', {}) or {}
        alma = num.get('alma', {}) or {}
        numerology_min = (
            f"Ano pessoal {ano_pess.get('numero','?')}, "
            f"Caminho de vida {caminho.get('numero','?')}, "
            f"Alma {alma.get('numero','?')}"
        )

        # 3) Astrologia: só diretrizes (que JÁ são resumos canônicos)
        ast = user.astrology_data or {}
        sol = ast.get('diretrizes_sol', {}) or {}
        asc = ast.get('diretrizes_ascendente', {}) or {}
        ast_sol_tom = (sol.get('tom', '') or '')[:60]
        ast_sol_cuidado = (sol.get('cuidado', '') or '')[:80]
        ast_asc_tom = (asc.get('tom', '') or '')[:60]
        ast_asc_cuidado = (asc.get('cuidado', '') or '')[:80]
        astrology_min = (
            f"Sol ({ast_sol_tom}): {ast_sol_cuidado}. "
            f"Ascendente ({ast_asc_tom}): {ast_asc_cuidado}"
        )

        return onboarding_min, numerology_min, astrology_min

    async def _extract_user_history(self, db: AsyncSession, user) -> str:
        """Histórico recente de análises/alertas do user — detecta padrão."""
        # Últimas 3 análises (independente do nível)
        ana_res = await db.execute(
            select(models.SupervisorAnalysis)
            .where(models.SupervisorAnalysis.user_id == user.id)
            .order_by(models.SupervisorAnalysis.created_at.desc())
            .limit(3)
        )
        recent_anas = list(ana_res.scalars().all())

        # Alertas abertos atualmente
        alerts_res = await db.execute(
            select(models.SupervisorAlert)
            .where(
                models.SupervisorAlert.user_id == user.id,
                models.SupervisorAlert.status.in_(["open", "acknowledged"]),
            )
            .order_by(models.SupervisorAlert.created_at.desc())
            .limit(3)
        )
        open_alerts = list(alerts_res.scalars().all())

        parts = []
        if open_alerts:
            lvls = ', '.join(f"{a.level}" for a in open_alerts[:3])
            parts.append(f"⚠️ Alertas abertos: {lvls}")

        if recent_anas:
            trends = ', '.join(f"{a.level}({a.score:.2f})" for a in recent_anas[:3])
            parts.append(f"Últimas análises: {trends}")

        return ' | '.join(parts) if parts else "(sem histórico)"

    async def create_alert_if_needed(
        self,
        db: AsyncSession,
        analysis: models.SupervisorAnalysis,
    ) -> Optional[models.SupervisorAlert]:
        """Cria alerta se análise for ATENCAO/URGENCIA. Retorna o alerta criado ou None."""
        if analysis.level == "NORMAL":
            return None

        # Verifica se já tem alerta ABERTO do mesmo user + mesmo nível
        existing_res = await db.execute(
            select(models.SupervisorAlert)
            .where(
                models.SupervisorAlert.user_id == analysis.user_id,
                models.SupervisorAlert.level == analysis.level,
                models.SupervisorAlert.status.in_(["open", "acknowledged"]),
            )
            .order_by(models.SupervisorAlert.created_at.desc())
            .limit(1)
        )
        existing = existing_res.scalar_one_or_none()

        # Pega excerpt da mensagem original UMA vez (usado nos dois caminhos)
        msg_res = await db.execute(
            select(models.Message).where(models.Message.id == analysis.message_id)
        )
        msg = msg_res.scalar_one_or_none()

        if existing:
            # Incrementa ocorrências
            existing.occurrences = (existing.occurrences or 1) + 1
            existing.last_occurrence_at = datetime.utcnow()
            # ATUALIZA excerpt com a msg real (se possível) — antes sobrescrevia
            # com analysis.reason ("Padrão crítico detectado por regex") e o admin
            # não via o que o user de fato mandou. Melhor manter o texto real.
            if msg:
                existing.message_excerpt = msg.content[:500]
            # Promove pra IA-confirmado se essa nova análise for IA
            if self._is_ia_model(analysis.model_used):
                existing.ia_confirmed = True
            await db.commit()
            return existing

        # Cria novo alerta
        title = (
            f"🚨 URGÊNCIA — ação imediata necessária"
            if analysis.level == "URGENCIA"
            else f"⚠️ ATENÇÃO — usuário precisa acompanhamento"
        )

        # Pega excerpt da mensagem original (já carregado acima)
        excerpt = (msg.content[:300] if msg else "") if msg else ""

        alert = models.SupervisorAlert(
            user_id=analysis.user_id,
            analysis_id=analysis.id,
            level=analysis.level,
            status="open",
            title=title,
            message=analysis.reason,
            message_excerpt=excerpt,
            occurrences=1,
            last_occurrence_at=datetime.utcnow(),
            # IA confirmou = análise veio de modelo IA (MiniMax-M3 etc), não só regex
            ia_confirmed=self._is_ia_model(analysis.model_used),
        )
        db.add(alert)
        await db.commit()
        await db.refresh(alert)

        logger.warning(
            f"{'🚨' if analysis.level == 'URGENCIA' else '⚠️'} "
            f"Alerta criado: level={analysis.level} user={analysis.user_id}"
        )
        return alert

    async def get_ayria_auto_response(
        self,
        level: str,
    ) -> Optional[str]:
        """
        Retorna mensagem automática da Ayria pra inserir na conversa em casos críticos.
        None se nível NORMAL.
        """
        if level == "URGENCIA":
            return (
                "Percebi que você mencionou coisas que me preocupam muito. "
                "Você não está sozinho(a), e existe ajuda especializada disponível **agora**:\n\n"
                "📞 **CVV — Centro de Valorização da Vida**\n"
                "Ligue **188** (24h, gratuito e sigiloso)\n"
                "Ou acesse cvv.org.br\n\n"
                "Eu estou aqui pra te ouvir, mas o CVV tem profissionais treinados pra te ajudar "
                "da melhor forma possível. Posso continuar conversando com você, mas por favor, "
                "considere ligar 188 — sua vida tem valor. ❤️"
            )
        if level == "ATENCAO":
            return (
                "Sinto que algo importante tá te incomodando. Quero te ouvir com atenção. "
                "Se você quiser, pode me contar mais sobre o que tá sentindo — sem pressa, "
                "sem julgamento. Estou aqui. 🤍"
            )
        return None


# Singleton
supervisor_service = SupervisorService()
