"""
Schemas de KnowledgeDocument.
"""
from typing import Optional
from pydantic import BaseModel

from ._base import uuid, datetime


class KnowledgeDocumentResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str]
    file_name: Optional[str]
    file_size_bytes: Optional[int]
    storage_url: Optional[str] = None
    storage_provider: Optional[str] = None
    status: str
    chunks_count: int
    indexed_at: Optional[datetime]
    collection: str
    created_at: datetime

    class Config:
        from_attributes = True
