"""
Imports compartilhados por todos os arquivos de models.
Centraliza os imports SQLAlchemy pra evitar repetição.
"""
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, DateTime, Date, ForeignKey,
    UniqueConstraint, CheckConstraint, Index, BigInteger, JSON, Numeric, SmallInteger
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid

from database import Base


def gen_uuid():
    return uuid.uuid4()
