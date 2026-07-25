"""
Imports compartilhados por todos os arquivos do admin router.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update as _upd, text as sql_text
import uuid
import logging
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from database import get_db
from utils.security import require_admin, hash_password, get_client_ip, get_user_agent
from services.storage_service import storage_service
from services import credit_service
import models
import schemas


# Cada arquivo declara seu próprio router e o __init__.py junta tudo
# Isso permite imports circulares entre sub-arquivos do admin sem dor.

logger = logging.getLogger(__name__)
