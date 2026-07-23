"""
AYRIA - Prompt Selector (Classificador de Intenção V1)

Decide quais módulos carregar dinamicamente baseado em:
- Mensagem do user (regex/keywords)
- Perfil do user (onboarding, role, spiritual_preference)
- Contexto (admin, memórias, perfil numerológico/astrológico calculado)

Retorna dict com:
- modulos: lista de chaves de módulos a carregar
- flags: dict com flags situacionais (crise, admin, etc)
- reason: dict explicando POR QUE cada módulo foi escolhido (pra debug)
"""
import re
from pathlib import Path
from typing import Any

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

# Lista de módulos disponíveis (carregada do filesystem)
AVAILABLE_MODULES = sorted([
    p.stem.replace("prompt_", "") for p in PROMPTS_DIR.glob("prompt_*.md")
])
# Remove 'base' (é a constituição, sempre carregada separadamente)
AVAILABLE_MODULES = [m for m in AVAILABLE_MODULES if m != "base"]

# Mapeamento de keywords por módulo (regex case-insensitive)
KEYWORDS = {
    "numerologia": [
        r"\bnumerologia\b", r"\bnúmero da sorte\b", r"\bcaminho de vida\b",
        r"\bnúmero de expressão\b", r"\bnúmero da alma\b", r"\bano pessoal\b",
        r"\bcalcul.* numerolog", r"\bmeu número\b",
    ],
    "astrologia": [
        r"\bsigno\b", r"\bastrolog", r"\bmapa astral\b", r"\bascendente\b",
        r"\bsol em\b", r"\blua em\b", r"\bmeu signo\b", r"\bhoróscopo\b",
        r"\bcasas(astral|planetária)", r"\bplaneta\b",
    ],
    "psicologia": [
        r"\bpsicolog", r"\bterapia\b", r"\bterapeuta\b", r"\bansiedade\b",
        r"\bdepress", r"\bestresse\b", r"\bautoestima\b", r"\bburnout\b",
        r"\bpânico\b", r"\bfobia\b", r"\btdah\b", r"\btoc\b",
        r"\bcomportament", r"\bgatilho emocional\b", r"\bcogniti[fv]o?\b",
    ],
    "psicanalise": [
        r"\bpsicanáli", r"\bfreud", r"\bjung\b", r"\blacan\b",
        r"\binconsciente\b", r"\bsonho\b", r"\bsonho recorrente\b",
        r"\barquétipo\b", r"\bsombra\b", r"\bedipiano\b", r"\bmecanismo de defesa\b",
        r"\brepetição de padrão\b",
    ],
    "psicologia_clinica": [
        # Diagnósticos / condições clínicas
        r"\bdsm\b", r"\bcid\b", r"\bdiagn[óo]stic", r"\bsintomas\b",
        r"\btranstorno\b", r"\bdepress[ãa]o maior\b", r"\btag\b", r"\btoc\b",
        r"\btdah\b", r"\bbipolar\b", r"\bman[ií]a\b", r"\bhipoman", r"\btept\b",
        r"\bp[âa]nico\b", r"\bfobia social\b", r"\bschizofrenia\b",
        r"\bborderline\b", r"\bautism", r"\btourette\b",
        # Medicação (nomes comerciais E genéricos)
        r"\bfluoxetina\b", r"\bprozac\b", r"\bsertralina\b", r"\bzoloft\b",
        r"\bescitalopram\b", r"\blexapro\b", r"\bparoxetina\b", r"\bpaxil\b",
        r"\bvenlafaxina\b", r"\bclonazepam\b", r"\britonil\b", r"\balprazolam\b",
        r"\bdiazepam\b", r"\bvalium\b", r"\brivotril\b", r"\bl[ií]tio\b",
        r"\brisperidona\b", r"\bquetiapina\b", r"\bolanzapina\b",
        r"\bantidepressivo\b", r"\bpsicof[áa]rmaco\b", r"\bmedica[çc][ãa]o\b",
        r"\bmedicament", r"\btomando (remédio|rem[ée]dio|medicamento)\b",
        r"\btomo (remédio|rem[ée]dio|medicamento)\b",
        r"\befeito(s)? colateral\b", r"\bantipsic[óo]tic", r"\bestabilizador\b",
        # Escalas
        r"\bphq-?9\b", r"\bgad-?7\b", r"\bpss-?10\b", r"\bphq\b", r"\bgad\b",
        r"\bescala.*depress", r"\bescala.*ansiedade",
        r"\bavalia[çc][ãa]o\b", r"\btriagem\b",
        # Encaminhamento
        r"\bpsiquiatra\b", r"\bquer[oa].*psic[óo]log", r"\bquer[oa].*psicanal",
        r"\bcomo (achar|encontrar|procurar).*(psic[óo]log|psicanal|terapeuta)",
        r"\bpreciso.*(psic[óo]log|psicanal|terapeuta)\b",
        r"\bconv[eê]nio\b.*psic", r"\bzenklub\b", r"\bvittude\b", r"\bmoodar\b",
        r"\bcaps\b", r"\bsus\b.*psic",
        # Abordagens
        r"\btcc\b", r"\bdbt\b", r"\bact\b", r"\bifs\b",
        r"\bterapia.*esquema\b", r"\blogoterapia\b",
        r"\bterapia cognitivo", r"\bterapia comportamental\b",
    ],
    "religiao": [
        r"\bdeus\b", r"\bjesus\b", r"\bbíblia\b", r"\boração\b", r"\bfé\b",
        r"\breligião\b", r"\bespiritual", r"\bislam\b", r"\bjudaísmo\b",
        r"\bcristã", r"\bcatólic", r"\bevang", r"\bespirita\b",
        r"\bbudismo\b", r"\balma\b(?! da ayria)",
    ],
    "visao_mundo": [
        r"\bcatóli", r"\bevang", r"\bespirita\b", r"\bbudist",
        r"\bateu\b", r"\bagnóstic", r"\bexistencialism",
    ],
    "seguranca_crise": [
        # PRIORIDADE MÁXIMA — Nível 1 (suicídio/homicídio/autolesão)
        r"\bquero morrer\b", r"\bvou me matar\b", r"\bme matar\b",
        r"\bsuicid", r"\bme machucar\b", r"\bme cortar\b",
        r"\bme explodir\b", r"\btirar (a |minha )vida\b",
        r"\bnão vou (estar |viver )mais\b", r"\bacabar com tudo\b",
        r"\bvou (sumir|desaparecer)\b", r"\bplano (de morte|suicídio|matar)\b",
        r"\bvou (matar|fazer ele sofrer) (alguém|ele|ela)\b",
        # Nível 2 (crimes/violência)
        r"\bvou (roubar|tráfico|traficar|agredir|estuprar)\b",
        r"\bviolência doméstica\b", r"\bmeu parceiro me bate\b",
        r"\bestou pensando em matar (ele|ela|alguém)\b",
        # Nível 3 (vícios/compulsões)
        r"\bvício em (apostas|jogo|cassino)\b", r"\bjogatina\b",
        r"\btranstorno alimentar\b", r"\banorexia\b", r"\bbulimia\b",
        r"\boverdose\b", r"\bálcool (demais|em excesso)\b",
        r"\bdrogas (demais|em excesso)\b",
        # Crise emocional (genérico)
        r"\bnão aguento mais\b", r"\bnão suporto mais\b",
        r"\bdesespero\b", r"\bsem saída\b", r"\bsem esperança\b",
        r"\bnão tenho motivos\b", r"\bseria melhor se eu não existisse\b",
    ],
    "luto": [
        r"\bfaleceu\b", r"\bmorte de\b", r"\bmorreu\b",
        r"\benterr", r"\bfuneral\b", r"\bvelório\b",
        r"\bhomenagem póstuma\b",
        # 'perdi' sozinho é ambíguo demais, melhor não usar
    ],
    "relacionamentos": [
        r"\bnamorad[oa]?\b", r"\bcônjuge\b", r"\bespos[oa]\b",
        r"\bcasal\b", r"\bfamília\b", r"\bpai\b", r"\bmãe\b",
        r"\bmarido\b", r"\besposa\b", r"\bnamor\w+",
        r"\bamigo\b", r"\bamizade\b", r"\bconflito\b",
        r"\btraição\b", r"\bseparaç\w+", r"\babuso\b",
        r"\bviolência doméstica\b", r"\bcuidar dos filhos\b",
        r"\bminha mãe\b", r"\bmeu pai\b", r"\bbrig\w+ com\b",
        r"\btermin\w+ (com|relacionamento)", r"\bfilhos\b",
    ],
    "carreira": [
        r"\btrabalho\b", r"\bemprego\b", r"\bcarreira\b", r"\bprofiss",
        r"\bchefe\b", r"\bdemiti[dpr]?\w*", r"\bpromoç\w+", r"\bcolega de trabalho\b",
        r"\bdesempregad", r"\bentrevist", r"\bvocação\b",
        r"\bpropósito profissional\b",
        r"\bpedir demiss\w+", r"\bme demit\w+", r"\bdemitir\b",
    ],
    "logs": [
        # Termos que indicam relato de erro / bug
        r"\bdeu erro\b", r"\bdeu pau\b", r"\btravou\b", r"\bcaiu\b",
        r"\bnão funciona\b", r"\bnão tá funcionando\b", r"\bnão carrega\b",
        r"\bbug\b", r"\bbugou\b", r"\bfalho[u]?\b", r"\bfalha\b",
        r"\btimeout\b", r"\btempo esgotado\b",
        r"\bexceç\w+\b", r"\bexception\b", r"\berr[oa] 500\b", r"\berr[oa] 404\b",
        r"\berr[oa] 401\b", r"\berr[oa] 403\b", r"\berr[oa] 429\b",
        r"\bstatus 5\d{2}\b", r"\bstatus 4\d{2}\b",
        r"\bstack ?trace\b", r"\btraceback\b",
        r"\bnão conseguiu\b", r"\bnão consegue\b",
        r"\bnão consigo\b", r"\bdeu ruim\b",
        r"\bpantalla (azul|preta)\b", r"\btela azul\b", r"\btela preta\b",
        r"\b(instável|instavel)\b", r"\blentidão\b", r"\bdemorou (muito|demais)\b",
        r"❌", r"⚠️",
    ],
}


def _matches_any(text: str, patterns: list[str]) -> bool:
    """Verifica se o texto bate com pelo menos um padrão."""
    text_lower = text.lower()
    for p in patterns:
        if re.search(p, text_lower, re.IGNORECASE):
            return True
    return False


def classify(
    user_message: str,
    user: Any,
    history: list = None,
    has_memories: bool = False,
    has_numerology: bool = False,
    has_astrology: bool = False,
    has_spiritual_preference: bool = False,
) -> dict:
    """
    Classifica intenção e retorna módulos a carregar.

    Args:
        user_message: Conteúdo da mensagem atual do user
        user: Objeto User (precisa ter .role, .onboarding_status)
        history: Lista de mensagens anteriores (opcional)
        has_memories: Se há memórias relevantes recuperadas
        has_numerology: Se o user tem numerologia calculada
        has_astrology: Se o user tem astrologia calculada
        has_spiritual_preference: Se o user tem spiritual_preference preenchida

    Returns:
        {
            "modulos": ["numerologia", "psicologia"],
            "flags": {"crise": True, "admin": False, ...},
            "reason": {"numerologia": "mencionou na msg + tem no perfil", ...}
        }
    """
    modulos: list[str] = []
    reasons: dict[str, str] = {}
    flags: dict[str, bool] = {
        "crise": False,
        "admin": False,
        "onboarding_pendente": False,
        "tem_memoria": False,
        "tem_numerologia": False,
        "tem_astrologia": False,
        "tem_spiritual": False,
    }

    # ============ PRIORIDADE MÁXIMA: SEGURANÇA E CRISE ============
    if _matches_any(user_message, KEYWORDS["seguranca_crise"]):
        modulos.append("seguranca_crise")
        reasons["seguranca_crise"] = "ALERTA: sinais de risco detectados (Nível 1/2/3)"
        flags["crise"] = True

    # ============ CONTEXTO (sempre se ativo) ============
    # Admin (contexto administrativo)
    if getattr(user, "role", None) in ("admin", "SUPER_ADMIN"):
        flags["admin"] = True
        # Adiciona modulo_admin só se a mensagem parece administrativa
        msg_admin_keywords = [
            r"\bconfigur", r"\busuári", r"\bplano\b", r"\bcrédito",
            r"\bsistema\b", r"\bajust", r"\bcriar\b", r"\bdelet",
            r"\beditar\b", r"\binativa", r"\bativ",
        ]
        if _matches_any(user_message, msg_admin_keywords):
            modulos.append("admin")
            reasons["admin"] = "user é admin + mensagem parece administrativa"

    # Onboarding pendente
    if getattr(user, "onboarding_status", "completed") != "completed":
        flags["onboarding_pendente"] = True
        modulos.append("onboarding")
        reasons["onboarding"] = f"onboarding_status={user.onboarding_status}"

    # Memórias disponíveis
    if has_memories:
        flags["tem_memoria"] = True
        modulos.append("memoria")
        reasons["memoria"] = f"há memórias relevantes (N={history or 0})"

    # ============ POR PERFIL (dados calculados) ============
    if has_numerology:
        flags["tem_numerologia"] = True
        # Só carrega numerologia se user tem dados OU mencionou
        if _matches_any(user_message, KEYWORDS["numerologia"]):
            modulos.append("numerologia")
            reasons["numerologia"] = "user tem numerologia + mencionou na msg"
        # Se a conversa é sobre autoconhecimento genérico, numera entra também
        elif _matches_any(user_message, [r"\bautoconhec", r"\bpersonalidad", r"\btendência"]):
            modulos.append("numerologia")
            reasons["numerologia"] = "user tem numerologia + msg sobre autoconhecimento"

    if has_astrology:
        flags["tem_astrologia"] = True
        if _matches_any(user_message, KEYWORDS["astrologia"]):
            modulos.append("astrologia")
            reasons["astrologia"] = "user tem mapa astral + mencionou signo/astrologia"

    if has_spiritual_preference:
        flags["tem_spiritual"] = True
        # Visão de mundo entra se o user tem preferência espiritual E fala sobre
        if _matches_any(user_message, KEYWORDS["visao_mundo"]):
            modulos.append("visao_mundo")
            reasons["visao_mundo"] = "user tem preferência espiritual + msg sobre isso"

    # ============ DETECÇÃO POR MENSAGEM (temas da conversa) ============
    tema_checks = [
        ("psicologia", "psicologia"),
        ("psicanalise", "psicanálise"),
        ("relacionamentos", "relacionamentos"),
        ("carreira", "carreira"),
        ("luto", "luto"),
        ("religiao", "religião"),
        ("logs", "erros/bugs"),
    ]
    for mod_key, label in tema_checks:
        if _matches_any(user_message, KEYWORDS[mod_key]):
            if mod_key not in modulos:
                modulos.append(mod_key)
                reasons[mod_key] = f"mencionou termo de {label} na mensagem"

    # 🆕 22/07 23:08 — Psicologia clínica ativa em paralelo com psicologia/psicanálise
    # Trás DSM-5, escalas, psicofármacos, encaminhamento
    if "psicologia" in modulos or "psicanalise" in modulos:
        if _matches_any(user_message, KEYWORDS.get("psicologia_clinica", [])):
            if "psicologia_clinica" not in modulos:
                modulos.append("psicologia_clinica")
                reasons["psicologia_clinica"] = "sinais clínicos detectados (sintomas específicos, medicação, escalas)"

    # 🆕 22/07 23:08 — Protocolo de crise estruturado
    # Ativado em paralelo com seguranca_crise para forçar estrutura de resposta validada
    if flags.get("crise"):
        if "crise_protocolo" not in modulos:
            modulos.insert(0, "crise_protocolo")  # posição 0 = prioridade máxima
            reasons["crise_protocolo"] = "crise detectada → protocolo estruturado ativado"

    return {
        "modulos": modulos,
        "flags": flags,
        "reason": reasons,
    }


def load_constitution() -> str:
    """Carrega a constituição base (sempre)."""
    p = PROMPTS_DIR / "prompt_base.md"
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


def load_modules(module_keys: list[str], db_overrides: dict = None) -> list[str]:
    """
    Carrega o conteúdo dos módulos solicitados.
    Ordem: na ordem de module_keys.
    db_overrides: dict {key: content} se admin editou o módulo no banco.

    Módulos especiais:
      - "logs": injeta dinamicamente o conteúdo do .md + últimos erros do sistema
    """
    db_overrides = db_overrides or {}
    contents = []
    for key in module_keys:
        # Prioridade: override do banco > arquivo .md
        if key in db_overrides and db_overrides[key]:
            contents.append(f"# === MÓDULO: {key.upper()} (customizado pelo admin) ===\n\n{db_overrides[key]}")
            continue

        # 1ª opção: prompts/prompt_<key>.md (módulo normal)
        # 2ª opção: prompts/supervisor/<key>.md (módulo crítico do supervisor)
        # 3ª opção: placeholder
        p_normal = PROMPTS_DIR / f"prompt_{key}.md"
        p_supervisor = PROMPTS_DIR / "supervisor" / f"{key}.md"
        p = p_supervisor if p_supervisor.exists() else p_normal

        if p.exists():
            content = p.read_text(encoding="utf-8")

            # MÓDULO ESPECIAL: LOGS — anexa últimos erros do sistema em tempo real
            if key == "logs":
                content = _inject_recent_errors(content)

            contents.append(content)
        else:
            contents.append(f"# === MÓDULO: {key.upper()} ===\n\n(módulo não encontrado)")
    return contents


def _inject_recent_errors(module_content: str) -> str:
    """
    Anexa os últimos N erros do log do sistema ao módulo `logs`.
    Se o arquivo de log não existir (backend ainda não gravou nada),
    deixa só o conteúdo do .md.
    """
    try:
        import os
        import glob
        import re
        from datetime import datetime, timezone

        log_dir = os.getenv("AYRIA_LOG_DIR", "/app/logs")
        files = sorted(glob.glob(os.path.join(log_dir, "ayria.log*")), key=os.path.getmtime, reverse=True)
        if not files:
            return module_content + "\n\n## LOGS DO SISTEMA (tempo real)\n\n_Nenhum log encontrado ainda em `" + log_dir + "` — backend ainda não gravou nada._\n"

        main_log = files[0]
        with open(main_log, "r", encoding="utf-8", errors="replace") as f:
            content = f.readlines()

        # Detecta erros (mesma regex do endpoint /debug/errors)
        patterns = [
            r"\bERROR\b", r"\bEXCEPTION\b", r"\bTraceback\b", r"\bUNCAUGHT\b",
            r"❌", r"\bFailed\b", r"status: \d{3}.*[45]\d{2}",
        ]
        regex = re.compile("|".join(patterns), re.IGNORECASE)
        errors = [ln.rstrip() for ln in content if regex.search(ln)]
        last_errors = errors[-20:]  # últimos 20

        size = os.path.getsize(main_log)
        mod_time = datetime.fromtimestamp(os.path.getmtime(main_log), timezone.utc).isoformat()

        injection = (
            "\n\n## LOGS DO SISTEMA (tempo real — lido agora)\n\n"
            f"- **Arquivo:** `{main_log}` ({size:,} bytes)\n"
            f"- **Última modificação:** {mod_time}\n"
            f"- **Erros nas últimas linhas:** {len(last_errors)} (mostrando até 20)\n\n"
            "```\n"
            + ("\n".join(last_errors) if last_errors else "_(nenhum erro recente)_")
            + "\n```\n"
        )
        return module_content + injection
    except Exception as e:
        return module_content + f"\n\n## LOGS DO SISTEMA\n\n_⚠️ Falha ao ler log: {e}_\n"