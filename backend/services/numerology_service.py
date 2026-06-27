"""
AYRIA - Numerology Service

Calculos numerologicos baseados em dados do onboarding:
- Caminho de Vida (data nascimento)
- Expressao (nome completo)
- Alma (vogais do nome)
- Personalidade (consoantes do nome)
- Ano Pessoal (ano atual + caminho de vida)
"""
import re
from datetime import datetime
from typing import Dict, Optional, List


# Tabela Pitagórica
PITAGORICO = {
    'a': 1, 'b': 2, 'c': 3, 'd': 4, 'e': 5, 'f': 6, 'g': 7, 'h': 8, 'i': 9,
    'j': 1, 'k': 2, 'l': 3, 'm': 4, 'n': 5, 'o': 6, 'p': 7, 'q': 8, 'r': 9,
    's': 1, 't': 2, 'u': 3, 'v': 4, 'w': 5, 'x': 6, 'y': 7, 'z': 8,
}

VOGAIS = set('aeiouáéíóúâêîôûãõà')


def reduzir_numero(n: int, manter_mestres: bool = True) -> int:
    """Reduz número até virar 1-9 (ou 11, 22, 33 se for mestre)"""
    numeros_mestres = {11, 22, 33}
    while n > 9:
        if manter_mestres and n in numeros_mestres:
            return n
        n = sum(int(d) for d in str(n))
    return n


def calcular_caminho_vida(data_nascimento: str) -> Optional[dict]:
    """Calcula Caminho de Vida a partir da data DD/MM/AAAA ou YYYY-MM-DD"""
    nums = re.findall(r'\d+', data_nascimento)
    if len(nums) < 3:
        return None
    dia, mes, ano = int(nums[0]), int(nums[1]), int(nums[2])
    soma = dia + mes + ano
    reduzido = reduzir_numero(soma)
    return {
        "numero": reduzido,
        "eh_mestre": reduzido in (11, 22, 33),
        "calculo": f"{dia} + {mes} + {ano} = {soma} → {reduzido}",
    }


def calcular_expressao(nome: str) -> Optional[dict]:
    """Número de Expressão = soma de TODAS as letras do nome"""
    soma = sum(PITAGORICO.get(c.lower(), 0) for c in nome if c.isalpha() and c.lower() in PITAGORICO)
    if soma == 0:
        return None
    reduzido = reduzir_numero(soma)
    return {
        "numero": reduzido,
        "eh_mestre": reduzido in (11, 22, 33),
        "soma_bruta": soma,
    }


def calcular_alma(nome: str) -> Optional[dict]:
    """Número da Alma = soma só das VOGAIS do nome (desejos internos)"""
    soma = sum(
        PITAGORICO.get(c.lower(), 0)
        for c in nome
        if c.lower() in VOGAIS and c.lower() in PITAGORICO
    )
    if soma == 0:
        return None
    return {
        "numero": reduzir_numero(soma),
        "soma_bruta": soma,
    }


def calcular_personalidade(nome: str) -> Optional[dict]:
    """Número da Personalidade = soma só das CONSOANTES do nome (como você se mostra)"""
    soma = sum(
        PITAGORICO.get(c.lower(), 0)
        for c in nome
        if c.isalpha() and c.lower() not in VOGAIS and c.lower() in PITAGORICO
    )
    if soma == 0:
        return None
    return {
        "numero": reduzir_numero(soma),
        "soma_bruta": soma,
    }


def calcular_ano_pessoal(data_nascimento: str, ano_atual: Optional[int] = None) -> Optional[dict]:
    """Ano Pessoal = dia + mês de nascimento + ano atual"""
    nums = re.findall(r'\d+', data_nascimento)
    if len(nums) < 3:
        return None
    dia, mes, ano = int(nums[0]), int(nums[1]), int(nums[2])
    if ano_atual is None:
        ano_atual = datetime.now().year
    soma = dia + mes + ano_atual
    return {
        "numero": reduzir_numero(soma),
        "ano": ano_atual,
        "calculo": f"{dia} + {mes} + {ano_atual} = {soma} → {reduzir_numero(soma)}",
    }


def calcular_mapa_completo(attributes: Dict) -> Dict:
    """
    Calcula mapa numerológico completo baseado nos atributos preenchidos.
    
    Attributes esperados:
    - data_nascimento: "1990-05-15" ou "15/05/1990"
    - nome_completo: "Maria Silva Santos"
    - hora_nascimento: "14:30" (opcional, pra futuro)
    """
    mapa = {
        "calculado_em": datetime.utcnow().isoformat() + "Z",
        "dados_usados": {},
    }

    # Caminho de Vida
    if data := attributes.get("data_nascimento"):
        cv = calcular_caminho_vida(data)
        if cv:
            mapa["caminho_vida"] = cv
            mapa["dados_usados"]["data_nascimento"] = data

    # Expressão
    if nome := attributes.get("nome_completo"):
        expr = calcular_expressao(nome)
        if expr:
            mapa["expressao"] = expr

        # Alma
        alma = calcular_alma(nome)
        if alma:
            mapa["alma"] = alma

        # Personalidade
        pers = calcular_personalidade(nome)
        if pers:
            mapa["personalidade"] = pers

        mapa["dados_usados"]["nome_completo"] = nome

    # Ano Pessoal
    if data := attributes.get("data_nascimento"):
        ap = calcular_ano_pessoal(data)
        if ap:
            mapa["ano_pessoal"] = ap

    return mapa


# Interpretações resumidas (podem ser expandidas)
INTERPRETACOES = {
    1: {"palavras": ["Liderança", "Iniciativa", "Independência", "Pioneirismo"], "resumo": "Você é movido por liderança e iniciativa. Gosta de abrir caminhos."},
    2: {"palavras": ["Cooperação", "Diplomacia", "Sensibilidade", "Harmonia"], "resumo": "Você prospera em parcerias e busca equilíbrio. Mediador natural."},
    3: {"palavras": ["Criatividade", "Comunicação", "Alegria", "Expressão"], "resumo": "Você é criativo e se expressa com facilidade. Traz leveza onde está."},
    4: {"palavras": ["Estabilidade", "Trabalho", "Organização", "Disciplina"], "resumo": "Você constrói bases sólidas. Confiável e persistente."},
    5: {"palavras": ["Liberdade", "Aventura", "Versatilidade", "Mudança"], "resumo": "Você precisa de movimento e novidades. Liberdade é vital."},
    6: {"palavras": ["Amor", "Família", "Responsabilidade", "Cuidado"], "resumo": "Você cuida dos outros com amor. Família e lar são centrais."},
    7: {"palavras": ["Sabedoria", "Introspecção", "Espiritualidade", "Análise"], "resumo": "Você busca profundidade e verdade. Mente analítica e espiritual."},
    8: {"palavras": ["Poder", "Ambição", "Material", "Autoridade"], "resumo": "Você busca realização material e poder. Visionário executivo."},
    9: {"palavras": ["Humanitarismo", "Compaixão", "Idealismo", "Generosidade"], "resumo": "Você serve ao coletivo. Idealista e compassivo."},
    11: {"palavras": ["Intuição", "Inspiração", "Visão", "Mestre"], "resumo": "Número mestre. Intuição elevada e capacidade de inspirar multidões."},
    22: {"palavras": ["Construtor Mestre", "Visão Prática", "Legado"], "resumo": "Número mestre mais poderoso. Você constrói legados duradouros."},
    33: {"palavras": ["Mestre Curador", "Compaixão Total", "Servir"], "resumo": "Número mestre do amor incondicional. Cura através do exemplo."},
}


def interpretar_numero(n: int) -> dict:
    """Retorna interpretação básica de um número numerológico"""
    return INTERPRETACOES.get(n, {"palavras": [], "resumo": "Número fora do range padrão."})


def gerar_relatorio_numerologico(mapa: dict) -> str:
    """Gera texto narrativo do mapa numerológico para incluir no system prompt"""
    if not mapa or "caminho_vida" not in mapa:
        return "Mapa numerológico ainda não calculado."

    partes = []

    if "caminho_vida" in mapa:
        cv = mapa["caminho_vida"]
        interp = interpretar_numero(cv["numero"])
        partes.append(
            f"**Caminho de Vida {cv['numero']}{' (mestre)' if cv.get('eh_mestre') else ''}:** "
            f"{interp['resumo']} (Cálculo: {cv.get('calculo', 'N/A')})"
        )

    if "expressao" in mapa:
        expr = mapa["expressao"]
        interp = interpretar_numero(expr["numero"])
        partes.append(
            f"**Expressão {expr['numero']}:** {interp['resumo']}"
        )

    if "alma" in mapa:
        alma = mapa["alma"]
        interp = interpretar_numero(alma["numero"])
        partes.append(
            f"**Alma {alma['numero']}:** Seus desejos mais profundos se alinham com {', '.join(interp['palavras'])}."
        )

    if "personalidade" in mapa:
        pers = mapa["personalidade"]
        interp = interpretar_numero(pers["numero"])
        partes.append(
            f"**Personalidade {pers['numero']}:** Como você se mostra pro mundo: {interp['resumo']}"
        )

    if "ano_pessoal" in mapa:
        ap = mapa["ano_pessoal"]
        interp = interpretar_numero(ap["numero"])
        partes.append(
            f"**Ano Pessoal {ap['numero']} ({ap.get('ano', '')}):** {interp['resumo']}"
        )

    return "\n\n".join(partes)