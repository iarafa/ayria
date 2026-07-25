"""
Imports compartilhados por todos os arquivos do admin router.
Centraliza tudo que os sub-arquivos precisam.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, update as _upd, text as sql_text
import uuid
import logging
import json
import shutil
import time as _time
import urllib.request, urllib.error
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from database import get_db
from utils.security import require_admin, hash_password
from services.storage_service import storage_service
from services import credit_service
import models
import schemas


logger = logging.getLogger(__name__)
