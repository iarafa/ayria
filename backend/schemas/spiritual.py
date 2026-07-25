"""
Schemas de preferência religiosa/espiritual + lista de religiões suportadas.
"""
from typing import Optional, List
from pydantic import BaseModel

from ._base import uuid, datetime


# ============================================================
# SPIRITUAL PREFERENCES (Sistema 5)
# ============================================================
RELIGION_OPTIONS = [
    # Chave, Label, Emoji
    ("prefiro_nao_dizer",   "Prefiro não dizer",     "🤐"),
    ("ateu",                "Ateu / Ateísta",        "🧠"),
    ("agnostico",           "Agnóstico",             "🤔"),
    ("cristao_catolico",    "Cristianismo (Católico)", "✝️"),
    ("cristao_evangelico",  "Cristianismo (Evangélico)", "📖"),
    ("cristao_ortodoxo",    "Cristianismo (Ortodoxo)",   "☦️"),
    ("espirita_kardecista", "Espírita (Kardecista)", "📚"),
    ("espirita_livre",      "Espírita Livre",        "✨"),
    ("umbanda",             "Umbanda",               "🪘"),
    ("candomble",           "Candomblé",             "🥁"),
    ("santo_daime",         "Santo Daime / Ayahuasca","🌿"),
    ("judaísmo",            "Judaísmo",              "🕎"),
    ("islamismo",           "Islamismo",             "☪️"),
    ("budismo",             "Budismo",               "☸️"),
    ("hinduismo",           "Hinduísmo",             "🕉️"),
    ("testemunha_jeova",    "Testemunha de Jeová",   "🏛️"),
    ("espiritualista",      "Espiritualista / Messiânico", "🔮"),
    ("tradicao_indigena",   "Tradições Indígenas BR","🌎"),
    ("budista_secular",     "Budista Secular",       "🧘"),
    ("outro",               "Outra (descrever)",     "✏️"),
]


class SpiritualPreferenceResponse(BaseModel):
    user_id: uuid.UUID
    religion: str
    religion_label: Optional[str] = None
    religion_emoji: Optional[str] = None
    custom_label: Optional[str] = None
    custom_tags: List[str] = []
    notes: Optional[str] = None
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SpiritualPreferenceUpdate(BaseModel):
    religion: str
    custom_label: Optional[str] = None
    custom_tags: List[str] = []
    notes: Optional[str] = None
    is_active: bool = True


class ReligionOption(BaseModel):
    value: str
    label: str
    emoji: str


class ReligionOptionsResponse(BaseModel):
    options: List[ReligionOption]
