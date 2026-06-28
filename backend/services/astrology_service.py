"""
AYRIA - Astrology Service

Calcula mapa astral COMPLETO (sol, lua, ascendente, planetas, casas)
usando Kerykeion (Swiss Ephemeris offline) + geocoding local de cidades BR.

Tabela de cidades brasileiras (capitais + principais) em CIDADES_BR.
Fallback: pede coordenadas aproximadas pelo nome da cidade (match fuzzy).
"""
import os
import logging
from typing import Dict, Optional, List, Any
from datetime import datetime
import math

logger = logging.getLogger(__name__)
import re


def _parse_house(val) -> Optional[int]:
    """Kerykeion retorna string tipo 'First_House' — extrai número"""
    if val is None:
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        # "First_House", "Eighth_House", "Tenth_House" etc
        nums = {"First": 1, "Second": 2, "Third": 3, "Fourth": 4, "Fifth": 5,
                "Sixth": 6, "Seventh": 7, "Eighth": 8, "Ninth": 9, "Tenth": 10,
                "Eleventh": 11, "Twelfth": 12}
        for k, v in nums.items():
            if k in val:
                return v
        # Tenta extrair número
        m = re.search(r"\d+", val)
        return int(m.group()) if m else None
    return None


# =====================================================================
# TABELA DE CIDADES BRASILEIRAS (capitais + principais)
# Formato: nome_lower -> (latitude, longitude, timezone_str)
# =====================================================================
CIDADES_BR: Dict[str, tuple] = {
    # Capitais
    "sao paulo": (-23.5505, -46.6333, "America/Sao_Paulo"),
    "são paulo": (-23.5505, -46.6333, "America/Sao_Paulo"),
    "rio de janeiro": (-22.9068, -43.1729, "America/Sao_Paulo"),
    "brasilia": (-15.7942, -47.8825, "America/Sao_Paulo"),
    "brasília": (-15.7942, -47.8825, "America/Sao_Paulo"),
    "salvador": (-12.9714, -38.5014, "America/Bahia"),
    "fortaleza": (-3.7172, -38.5433, "America/Fortaleza"),
    "belo horizonte": (-19.9167, -43.9345, "America/Sao_Paulo"),
    "manaus": (-3.1190, -60.0217, "America/Manaus"),
    "curitiba": (-25.4284, -49.2733, "America/Sao_Paulo"),
    "recife": (-8.0476, -34.8770, "America/Recife"),
    "porto alegre": (-30.0346, -51.2177, "America/Sao_Paulo"),
    "belem": (-1.4558, -48.5024, "America/Belem"),
    "belém": (-1.4558, -48.5024, "America/Belem"),
    "goiania": (-16.6869, -49.2648, "America/Sao_Paulo"),
    "goiânia": (-16.6869, -49.2648, "America/Sao_Paulo"),
    "guarulhos": (-23.4538, -46.5333, "America/Sao_Paulo"),
    "campinas": (-22.9056, -47.0608, "America/Sao_Paulo"),
    "sao luiz": (-2.5297, -44.3028, "America/Fortaleza"),
    "sao luis": (-2.5297, -44.3028, "America/Fortaleza"),
    "são luís": (-2.5297, -44.3028, "America/Fortaleza"),
    "maceio": (-9.6498, -35.7089, "America/Maceio"),
    "maceió": (-9.6498, -35.7089, "America/Maceio"),
    "natal": (-5.7945, -35.2110, "America/Fortaleza"),
    "teresina": (-5.0892, -42.8016, "America/Fortaleza"),
    "campo grande": (-20.4697, -54.6201, "America/Campo_Grande"),
    "aracaju": (-10.9472, -37.0731, "America/Maceio"),
    "cuiaba": (-15.6014, -56.0979, "America/Cuiaba"),
    "cuiabá": (-15.6014, -56.0979, "America/Cuiaba"),
    "porto velho": (-8.7619, -63.9039, "America/Porto_Velho"),
    "boa vista": (2.8235, -60.6751, "America/Boa_Vista"),
    "florianopolis": (-27.5954, -48.5480, "America/Sao_Paulo"),
    "florianópolis": (-27.5954, -48.5480, "America/Sao_Paulo"),
    "joinville": (-26.3045, -48.8487, "America/Sao_Paulo"),
    "londrina": (-23.3045, -51.1696, "America/Sao_Paulo"),
    "uberlandia": (-18.9128, -48.2755, "America/Sao_Paulo"),
    "uberlândia": (-18.9128, -48.2755, "America/Sao_Paulo"),
    "ribeirao preto": (-21.1704, -47.8103, "America/Sao_Paulo"),
    "ribeirão preto": (-21.1704, -47.8103, "America/Sao_Paulo"),
    "sorocaba": (-23.5015, -47.4526, "America/Sao_Paulo"),
    "santos": (-23.9608, -46.3331, "America/Sao_Paulo"),
    "osasco": (-23.5325, -46.7916, "America/Sao_Paulo"),
    "sao bernardo do campo": (-23.6916, -46.5650, "America/Sao_Paulo"),
    "são bernardo do campo": (-23.6916, -46.5650, "America/Sao_Paulo"),
    "niteroi": (-22.8833, -43.1036, "America/Sao_Paulo"),
    "niterói": (-22.8833, -43.1036, "America/Sao_Paulo"),
    "petropolis": (-22.5050, -43.1786, "America/Sao_Paulo"),
    "petrópolis": (-22.5050, -43.1786, "America/Sao_Paulo"),
    "itatiba": (-23.0058, -46.8389, "America/Sao_Paulo"),
    "jundiai": (-23.1864, -46.8842, "America/Sao_Paulo"),
    "jundiaí": (-23.1864, -46.8842, "America/Sao_Paulo"),
    "mogi das cruzes": (-23.5225, -46.1883, "America/Sao_Paulo"),
    "sao jose do rio preto": (-20.8113, -49.3759, "America/Sao_Paulo"),
    "são josé do rio preto": (-20.8113, -49.3759, "America/Sao_Paulo"),
    "bauru": (-22.3147, -49.0606, "America/Sao_Paulo"),
    "sao jose dos campos": (-23.2237, -45.9009, "America/Sao_Paulo"),
    "são josé dos campos": (-23.2237, -45.9009, "America/Sao_Paulo"),
    "contagem": (-19.9320, -44.0539, "America/Sao_Paulo"),
    "juiz de fora": (-21.7642, -43.3496, "America/Sao_Paulo"),
    "betim": (-19.9678, -44.1983, "America/Sao_Paulo"),
    "montes claros": (-16.7350, -43.8617, "America/Sao_Paulo"),
    "anapolis": (-16.3281, -48.9531, "America/Sao_Paulo"),
    "anápolis": (-16.3281, -48.9531, "America/Sao_Paulo"),
    "florianopolis": (-27.5954, -48.5480, "America/Sao_Paulo"),
    "vitoria": (-20.3155, -40.3128, "America/Sao_Paulo"),
    "vitória": (-20.3155, -40.3128, "America/Sao_Paulo"),
    "serra": (-20.1210, -40.3073, "America/Sao_Paulo"),
    "vila velha": (-20.3297, -40.2922, "America/Sao_Paulo"),
    "cariacica": (-20.2632, -40.4165, "America/Sao_Paulo"),
    "maringa": (-23.4203, -51.9331, "America/Sao_Paulo"),
    "maringá": (-23.4203, -51.9331, "America/Sao_Paulo"),
    "foz do iguacu": (-25.5163, -54.5854, "America/Sao_Paulo"),
    "foz do iguaçu": (-25.5163, -54.5854, "America/Sao_Paulo"),
    "blumenau": (-26.9156, -49.0710, "America/Sao_Paulo"),
    "pelotas": (-31.7654, -52.3376, "America/Sao_Paulo"),
    "canoas": (-29.9177, -51.1834, "America/Sao_Paulo"),
    "caxias do sul": (-29.1678, -51.1794, "America/Sao_Paulo"),
    "viamao": (-30.0811, -51.0233, "America/Sao_Paulo"),
    "viamao": (-30.0811, -51.0233, "America/Sao_Paulo"),
    "novo hamburgo": (-29.6877, -51.1325, "America/Sao_Paulo"),
    "gravatai": (-29.9422, -50.9939, "America/Sao_Paulo"),
    "gravataí": (-29.9422, -50.9939, "America/Sao_Paulo"),
    "vitoria da conquista": (-14.8661, -40.8395, "America/Bahia"),
    "vitória da conquista": (-14.8661, -40.8395, "America/Bahia"),
    "ilheus": (-14.7884, -39.0462, "America/Bahia"),
    "ilhéus": (-14.7884, -39.0462, "America/Bahia"),
    "itabuna": (-14.7890, -39.2781, "America/Bahia"),
    "feira de santana": (-12.2664, -38.9663, "America/Bahia"),
    "camacari": (-12.6986, -38.3240, "America/Bahia"),
    "camaçari": (-12.6986, -38.3240, "America/Bahia"),
    "juazeiro": (-9.4116, -40.5036, "America/Bahia"),
    "petrolina": (-9.3891, -40.5024, "America/Bahia"),
    "caruaru": (-8.2836, -35.9761, "America/Recife"),
    "olinda": (-7.9981, -34.8458, "America/Recife"),
    "jaboatao dos guararapes": (-8.1127, -35.0150, "America/Recife"),
    "jaboatão dos guararapes": (-8.1127, -35.0150, "America/Recife"),
    "paulista": (-7.9440, -34.8730, "America/Recife"),
    "cabo": (-8.2827, -35.0344, "America/Recife"),
    "garanhuns": (-8.8904, -36.4928, "America/Recife"),
    "imperatriz": (-5.5264, -47.4758, "America/Fortaleza"),
    "sao jose de ribamar": (-2.5617, -44.0519, "America/Fortaleza"),
    "são josé de ribamar": (-2.5617, -44.0519, "America/Fortaleza"),
    "caxias": (-4.8590, -43.3558, "America/Fortaleza"),
    "timon": (-5.0970, -42.8368, "America/Fortaleza"),
    "picos": (-7.0784, -41.4672, "America/Fortaleza"),
    "juazeiro do norte": (-7.2128, -39.3150, "America/Fortaleza"),
    "crato": (-7.2341, -39.4175, "America/Fortaleza"),
    "sobral": (-3.6894, -40.3483, "America/Fortaleza"),
    "iguatu": (-6.3597, -39.2989, "America/Fortaleza"),
}


def geocode_cidade(nome_cidade: str) -> Optional[Dict[str, Any]]:
    """
    Busca coordenadas de uma cidade brasileira na tabela local.
    Retorna dict com lat, lon, timezone ou None se não achar.
    """
    if not nome_cidade:
        return None
    chave = nome_cidade.strip().lower()

    if chave in CIDADES_BR:
        lat, lon, tz = CIDADES_BR[chave]
        return {"lat": lat, "lon": lon, "timezone": tz, "cidade_original": nome_cidade}

    # Tenta match por substring (ex: usuário digitou "São Paulo - SP" → "São Paulo")
    for c, coords in CIDADES_BR.items():
        if c in chave or chave in c:
            lat, lon, tz = coords
            return {"lat": lat, "lon": lon, "timezone": tz, "cidade_original": nome_cidade}

    return None


# =====================================================================
# DIRETRIZES DE COMUNICAÇÃO POR SIGNO
# =====================================================================
SIGNOS_DIRETRIZES: Dict[str, Dict[str, Any]] = {
    "Áries": {
        "elemento": "Fogo",
        "qualidades": ["Corajoso", "Direto", "Energético", "Iniciador"],
        "tom": "Direto e motivador, sem rodeios",
        "abordagem": "Ação e desafios,激发ar iniciativa",
        "evitar": "Passividade e indecisão",
        "cuidado": "Impaciência — dar espaço para processar",
        "frases_tipo": ["Tá pronto pra agir?", "Qual o próximo passo concreto?"],
    },
    "Touro": {
        "elemento": "Terra",
        "qualidades": ["Estável", "Sensorial", "Prático", "Paciente"],
        "tom": "Calmo, ancorado, valorizando segurança",
        "abordagem": "Prático e sensorial, evitar abstrato demais",
        "evitar": "Pressa e mudanças bruscas",
        "cuidado": "Resistência a mudanças — oferecer segurança",
        "frases_tipo": ["Vamos com calma", "Que tal algo concreto?"],
    },
    "Gêmeos": {
        "elemento": "Ar",
        "qualidades": ["Curioso", "Comunicativo", "Versátil", "Rápido"],
        "tom": "Leve, curioso, com informação nova",
        "abordagem": "Variedade e estímulo mental, múltiplas perspectivas",
        "evitar": "Monotonia e excesso de profundidade",
        "cuidado": "Dispersão — focar em um tema por vez",
        "frases_tipo": ["Que interessante!", "Tem outros ângulos pra isso..."],
    },
    "Câncer": {
        "elemento": "Água",
        "qualidades": ["Emocional", "Cuidador", "Intuitivo", "Protetor"],
        "tom": "Acolhedor, validando sentimentos",
        "abordagem": "Conexão emocional e segurança afetiva",
        "evitar": "Frieza e racionalidade excessiva",
        "cuidado": "Sensibilidade — evitar críticas diretas",
        "frases_tipo": ["Como você tá se sentindo?", "Tô aqui pra te ouvir"],
    },
    "Leão": {
        "elemento": "Fogo",
        "qualidades": ["Criativo", "Generoso", "Líder", "Expressivo"],
        "tom": "Reconhecedor e caloroso",
        "abordagem": "Valorizar talentos e criatividade",
        "evitar": "Humildade forçada ou passar despercebido",
        "cuidado": "Orgulho — reconhecer sem bajular",
        "frases_tipo": ["Você brilha quando...", "Sua criatividade é única"],
    },
    "Virgem": {
        "elemento": "Terra",
        "qualidades": ["Analítico", "Detalhista", "Prático", "Exigente"],
        "tom": "Claro, organizado, com lógica",
        "abordagem": "Estrutura, planos, detalhes práticos",
        "evitar": "Ambiguidade e falta de plano",
        "cuidado": "Autocrítica — lembrar que merecem descanso",
        "frases_tipo": ["Vamos organizar?", "Um passo de cada vez"],
    },
    "Libra": {
        "elemento": "Ar",
        "qualidades": ["Diplomático", "Estético", "Justo", "Sociável"],
        "tom": "Harmônico, equilibrado, valorizando perspectiva",
        "abordagem": "Considerar todos os lados, beleza e justiça",
        "evitar": "Confronto direto e decisões bruscas",
        "cuidado": "Indecisão — ajudar a priorizar",
        "frases_tipo": ["Vamos ver os dois lados", "O que é mais importante pra você?"],
    },
    "Escorpião": {
        "elemento": "Água",
        "qualidades": ["Intenso", "Profundo", "Perceptivo", "Transformador"],
        "tom": "Profundo, respeitando intensidade",
        "abordagem": "Ir fundo, sem medo de intensidade",
        "evitar": "Superficialidade e frivolidade",
        "cuidado": "Suspeita — construir confiança gradual",
        "frases_tipo": ["Mergulha fundo nisso", "O que tá por trás disso?"],
    },
    "Sagitário": {
        "elemento": "Fogo",
        "qualidades": ["Aventureiro", "Otimista", "Filosófico", "Expansivo"],
        "tom": "Inspirador, com visão ampla",
        "abordagem": "Sentido maior, expansão, novas possibilidades",
        "evitar": "Detalhes pequenos e限制ções",
        "cuidado": "Impaciência com rotina — conectar com propósito",
        "frases_tipo": ["Qual o sentido maior?", "Onde isso te leva?"],
    },
    "Capricórnio": {
        "elemento": "Terra",
        "qualidades": ["Disciplinado", "Ambicioso", "Responsável", "Sério"],
        "tom": "Respeitoso, valorizando esforço e resultado",
        "abordagem": "Metas, planos, responsabilidade",
        "evitar": "Irresponsabilidade e falta de plano",
        "cuidado": "Rigidez — lembrar de celebrar conquistas",
        "frases_tipo": ["Qual seu próximo objetivo?", "Tá no caminho certo"],
    },
    "Aquário": {
        "elemento": "Ar",
        "qualidades": ["Original", "Independente", "Humanitário", "Inventivo"],
        "tom": "Respeitando individualidade, com ideias novas",
        "abordagem": "Inovação, visão de futuro, quebra de padrões",
        "evitar": "Tradição cega e convencionalismo",
        "cuidado": "Distância emocional — conectar com humanidade",
        "frases_tipo": ["E se a gente fizesse diferente?", "Qual sua visão?"],
    },
    "Peixes": {
        "elemento": "Água",
        "qualidades": ["Intuitivo", "Sonhador", "Compassivo", "Artístico"],
        "tom": "Suave, validando imaginação e sensibilidade",
        "abordagem": "Conexão espiritual, arte, compaixão",
        "evitar": "Lógica fria e rigidez",
        "cuidado": "Confusão entre fantasia e realidade — ancorar gentilmente",
        "frases_tipo": ["O que seu coração diz?", "Tá tudo bem sonhar"],
    },
}


SIGNOS_PT = {
    # Nomes completos
    "Aries": "Áries", "Taurus": "Touro", "Gemini": "Gêmeos", "Cancer": "Câncer",
    "Leo": "Leão", "Virgo": "Virgem", "Libra": "Libra", "Scorpio": "Escorpião",
    "Sagittarius": "Sagitário", "Capricorn": "Capricórnio", "Aquarius": "Aquário",
    "Pisces": "Peixes",
    # Abreviações Kerykeion v4
    "Ari": "Áries", "Tau": "Touro", "Gem": "Gêmeos", "Can": "Câncer",
    "Leo": "Leão", "Vir": "Virgem", "Lib": "Libra", "Sco": "Escorpião",
    "Sag": "Sagitário", "Cap": "Capricórnio", "Aqu": "Aquário", "Pis": "Peixes",
}


# =====================================================================
# ASTROLOGY SERVICE
# =====================================================================
class AstrologyService:
    """Calcula mapa astral completo"""

    def __init__(self):
        self._kerykeion_ok = self._check_kerykeion()

    def _check_kerykeion(self) -> bool:
        """Verifica se Kerykeion está instalado"""
        try:
            from kerykeion import AstrologicalSubject
            return True
        except ImportError:
            logger.warning("⚠️ Kerykeion não instalado — astrologia desabilitada")
            return False

    def calcular_mapa(
        self,
        nome: str,
        data_nascimento: str,  # YYYY-MM-DD
        hora_nascimento: str,    # HH:MM
        cidade: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Calcula mapa astral completo.

        Returns:
            Dict com signos, planetas, casas, aspectos — ou None se erro
        """
        if not self._kerykeion_ok:
            logger.error("Kerykeion não disponível")
            return self._fallback_solo_solar(data_nascimento)

        # Geocoding
        coords = geocode_cidade(cidade)
        if not coords:
            logger.warning(f"Cidade '{cidade}' não encontrada — usando São Paulo como default")
            coords = {"lat": -23.5505, "lon": -46.6333, "timezone": "America/Sao_Paulo"}

        try:
            from kerykeion import AstrologicalSubject

            # Parse data/hora
            ano, mes, dia = map(int, data_nascimento.split("-"))
            hora_parts = hora_nascimento.split(":") if hora_nascimento else ["12", "0"]
            hora = int(hora_parts[0])
            minuto = int(hora_parts[1]) if len(hora_parts) > 1 else 0

            # Cria subject (sem lat/lon porque Kerykeion precisa de string de timezone)
            subject = AstrologicalSubject(
                name=nome or "User",
                year=ano,
                month=mes,
                day=dia,
                hour=hora,
                minute=minuto,
                lng=coords["lon"],
                lat=coords["lat"],
                tz_str=coords["timezone"],
            )

            mapa = {
                "data_calculo": datetime.utcnow().isoformat() + "Z",
                "cidade_usada": coords.get("cidade_original", cidade),
                "coordenadas": {"lat": coords["lat"], "lon": coords["lon"]},
                "sol": {
                    "signo_pt": SIGNOS_PT.get(subject.sun.sign, str(subject.sun.sign)),
                    "signo_en": str(subject.sun.sign),
                    "posicao": float(subject.sun.position) if hasattr(subject.sun, "position") else None,
                    "casa": _parse_house(subject.sun.house) if hasattr(subject.sun, "house") else None,
                    "elemento": SIGNOS_DIRETRIZES.get(SIGNOS_PT.get(subject.sun.sign, ""), {}).get("elemento"),
                },
                "lua": {
                    "signo_pt": SIGNOS_PT.get(subject.moon.sign, str(subject.moon.sign)),
                    "signo_en": str(subject.moon.sign),
                    "posicao": float(subject.moon.position) if hasattr(subject.moon, "position") else None,
                    "casa": _parse_house(subject.moon.house) if hasattr(subject.moon, "house") else None,
                    "elemento": SIGNOS_DIRETRIZES.get(SIGNOS_PT.get(subject.moon.sign, ""), {}).get("elemento"),
                },
                "ascendente": {
                    "signo_pt": SIGNOS_PT.get(subject.first_house.sign, str(subject.first_house.sign)),
                    "signo_en": str(subject.first_house.sign),
                    "posicao": float(subject.first_house.position) if hasattr(subject.first_house, "position") else None,
                },
                "mercurio": self._planet(subject, "mercury"),
                "venus": self._planet(subject, "venus"),
                "marte": self._planet(subject, "mars"),
                "jupiter": self._planet(subject, "jupiter"),
                "saturno": self._planet(subject, "saturn"),
                "casas": self._casas(subject),
            }

            # Adiciona diretrizes do signo solar
            mapa["diretrizes_sol"] = SIGNOS_DIRETRIZES.get(mapa["sol"]["signo_pt"], {})
            mapa["diretrizes_ascendente"] = SIGNOS_DIRETRIZES.get(mapa["ascendente"]["signo_pt"], {})

            logger.info(f"✅ Mapa astral calculado: Sol={mapa['sol']['signo_pt']}, Asc={mapa['ascendente']['signo_pt']}")
            return mapa

        except Exception as e:
            logger.error(f"Erro calculando mapa astral: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return self._fallback_solo_solar(data_nascimento)

    def _planet(self, subject, name: str) -> Dict[str, Any]:
        """Helper: extrai info de um planeta"""
        try:
            planet = getattr(subject, name)
            return {
                "signo_pt": SIGNOS_PT.get(planet.sign, str(planet.sign)),
                "signo_en": str(planet.sign),
                "posicao": float(planet.position) if hasattr(planet, "position") else None,
                "casa": _parse_house(planet.house) if hasattr(planet, "house") else None,
                "elemento": SIGNOS_DIRETRIZES.get(SIGNOS_PT.get(planet.sign, ""), {}).get("elemento"),
            }
        except Exception:
            return {"signo_pt": "?", "signo_en": "?", "posicao": None, "casa": None, "elemento": None}

    def _casas(self, subject) -> Dict[int, str]:
        """Retorna signos das 12 casas"""
        casas = {}
        for i in range(1, 13):
            try:
                house = getattr(subject, f"{self._house_name(i)}_house")
                casas[i] = SIGNOS_PT.get(house.sign, str(house.sign))
            except Exception:
                casas[i] = "?"
        return casas

    def _house_name(self, n: int) -> str:
        if n == 1:
            return "first"
        elif n == 2:
            return "second"
        elif n == 3:
            return "third"
        elif n in [4, 5, 6, 7, 8, 9, 10, 11, 12]:
            return ["", "", "", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth", "eleventh", "twelfth"][n]
        # Fallback: tenta usar numeracao ordinal
        try:
            return ["first","second","third","fourth","fifth","sixth","seventh","eighth","ninth","tenth","eleventh","twelfth"][n-1] + "_house"
        except Exception:
            return f"house_{n}"
        return ""

    def _fallback_solo_solar(self, data_nascimento: str) -> Dict[str, Any]:
        """
        Fallback: só signo solar por data (sem Kerykeion)
        Baseado nas datas dos signos zodiacais
        """
        try:
            _, mes, dia = map(int, data_nascimento.split("-"))
        except Exception:
            return None

        # Datas dos signos (início, fim) — mês, dia
        signos_datas = [
            ("Capricórnio", 12, 22, 1, 19),
            ("Aquário", 1, 20, 2, 18),
            ("Peixes", 2, 19, 3, 20),
            ("Áries", 3, 21, 4, 19),
            ("Touro", 4, 20, 5, 20),
            ("Gêmeos", 5, 21, 6, 20),
            ("Câncer", 6, 21, 7, 22),
            ("Leão", 7, 23, 8, 22),
            ("Virgem", 8, 23, 9, 22),
            ("Libra", 9, 23, 10, 22),
            ("Escorpião", 10, 23, 11, 21),
            ("Sagitário", 11, 22, 12, 21),
        ]

        signo = "?"
        for nome, m1, d1, m2, d2 in signos_datas:
            if (mes == m1 and dia >= d1) or (mes == m2 and dia <= d2):
                signo = nome
                break

        return {
            "data_calculo": datetime.utcnow().isoformat() + "Z",
            "sol": {
                "signo_pt": signo,
                "signo_en": signo,
                "elemento": SIGNOS_DIRETRIZES.get(signo, {}).get("elemento"),
                "casa": None,
                "posicao": None,
            },
            "ascendente": {"signo_pt": "?", "signo_en": "?"},
            "lua": {"signo_pt": "?", "signo_en": "?"},
            "fallback": True,
            "diretrizes_sol": SIGNOS_DIRETRIZES.get(signo, {}),
        }

    def gerar_texto_perfil(self, mapa: Dict[str, Any]) -> str:
        """Gera texto descritivo do mapa pra usar no system prompt"""
        if not mapa:
            return ""

        sol = mapa.get("sol", {})
        asc = mapa.get("ascendente", {})
        lua = mapa.get("lua", {})
        diretrizes_sol = mapa.get("diretrizes_sol", {})

        texto = f"""**PERFIL ASTROLÓGICO (calculado silenciosamente)**:
- Sol em {sol.get('signo_pt', '?')} ({sol.get('elemento', '?')})
- Ascendente em {asc.get('signo_pt', '?')}
- Lua em {lua.get('signo_pt', '?')}

**Como falar com este usuário**:
- Tom: {diretrizes_sol.get('tom', 'respeitoso')}
- Abordagem: {diretrizes_sol.get('abordagem', 'autêntica')}
- Evitar: {diretrizes_sol.get('evitar', 'julgamento')}
- Cuidado: {diretrizes_sol.get('cuidado', 'não presuma nada')}
- Frases naturais pra usar: {', '.join(diretrizes_sol.get('frases_tipo', [])[:2])}
"""
        return texto


# Singleton
astrology_service = AstrologyService()