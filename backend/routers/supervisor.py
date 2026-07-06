"""
AYRIA - Supervisor Router (admin-only)
Endpoints de monitoramento de risco:
- GET /api/admin/supervisor/dashboard   → visão geral (contadores, lista de users em risco)
- GET /api/admin/supervisor/alerts      → lista de alertas (filtros: status, level)
- POST /api/admin/supervisor/alerts/{id}/acknowledge
- POST /api/admin/supervisor/alerts/{id}/resolve
- POST /api/admin/supervisor/alerts/{id}/dismiss
- GET /api/admin/supervisor/users/{id}/timeline  → histórico de análises do user
- GET /api/admin/supervisor/users/{id}/analyses  → só as análises
- GET /api/admin/supervisor/analyses/{id}        → detalhe de 1 análise
"""
from datetime import datetime, date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, and_, or_
from pydantic import BaseModel, Field
import logging

from database import get_db
from utils.security import require_admin
import models

router = APIRouter(prefix="/api/admin/supervisor", tags=["supervisor"])
logger = logging.getLogger(__name__)


# ============================================================
# SCHEMAS
# ============================================================
class DashboardCounters(BaseModel):
    total_users: int
    total_analyses_24h: int
    open_alerts: int
    urgencia_alerts: int
    atencao_alerts: int
    users_in_urgencia: int
    users_in_atencao: int
    # Contadores por nível de risco (3 níveis do prompt oficial)
    nivel1_alerts_24h: int = 0   # análises N1 (24h, TODAS — inclui dispensadas)
    nivel2_alerts_24h: int = 0
    nivel3_alerts_24h: int = 0
    # 🆕 Alertas ABERTOS por nível (24h, EXCLUI dispensados/resolvidos)
    open_nivel1: int = 0
    open_nivel2: int = 0
    open_nivel3: int = 0
    analyses_by_sublevel_24h: dict = {}  # {1: int, 2: int, 3: int}
    analyses_by_level: dict  # {NORMAL: int, ATENCAO: int, URGENCIA: int}


class UserRiskInfo(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    avatar_url: Optional[str]
    current_level: str
    max_score_24h: float
    total_messages_24h: int
    last_analysis_at: Optional[str]
    open_alert_id: Optional[str]


class DashboardResponse(BaseModel):
    counters: DashboardCounters
    high_risk_users: list[UserRiskInfo]
    recent_urgencias: list[dict]
    generated_at: str


class AlertResponse(BaseModel):
    id: str
    user_id: str
    user_email: str
    user_full_name: Optional[str]
    user_avatar_url: Optional[str]
    level: str
    status: str
    title: str
    message: Optional[str]
    message_excerpt: Optional[str]
    # Adicionados pra acesso direto à mensagem no dashboard
    message_id: Optional[str] = None
    chat_id: Optional[str] = None
    occurrences: int
    acknowledged_by: Optional[str]
    acknowledged_at: Optional[str]
    resolved_by: Optional[str]
    resolved_at: Optional[str]
    resolution_notes: Optional[str]
    last_occurrence_at: str
    created_at: str
    risk_sublevel: Optional[int] = None  # 1|2|3 quando armazenado pelo pré-check
    ia_confirmed: Optional[bool] = None  # True=IA confirmou, False=aguarda batch, None=legado


class AlertListResponse(BaseModel):
    """Resposta paginada de alertas."""
    items: list[AlertResponse]
    total: int            # total de itens (sem filtro)
    offset: int
    limit: int
    has_next: bool        # se tem próxima página


class AnalysisResponse(BaseModel):
    id: str
    message_id: str
    user_id: str
    chat_id: str
    level: str
    score: float
    reason: Optional[str]
    recommended_action: Optional[str]
    signals: list[str]
    context_used: dict
    model_used: Optional[str]
    analysis_duration_ms: Optional[int]
    created_at: str
    message_excerpt: Optional[str]  # texto da msg que foi analisada


class AlertActionRequest(BaseModel):
    notes: Optional[str] = Field(None, max_length=2000)


# ============================================================
# DASHBOARD
# ============================================================
@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard(db: AsyncSession = Depends(get_db), admin=Depends(require_admin)):
    """Visão geral do sistema supervisor: contadores + users em risco + últimas urgências."""
    now = datetime.utcnow()
    last_24h = now - timedelta(hours=24)

    # Total users
    total_users_res = await db.execute(select(func.count(models.User.id)))
    total_users = total_users_res.scalar() or 0

    # Análises 24h
    analyses_24h_res = await db.execute(
        select(func.count(models.SupervisorAnalysis.id))
        .where(models.SupervisorAnalysis.created_at >= last_24h)
    )
    total_analyses_24h = analyses_24h_res.scalar() or 0

    # Análises por nível (24h)
    by_level_res = await db.execute(
        select(
            models.SupervisorAnalysis.level,
            func.count(models.SupervisorAnalysis.id),
        )
        .where(models.SupervisorAnalysis.created_at >= last_24h)
        .group_by(models.SupervisorAnalysis.level)
    )
    by_level = {row[0]: row[1] for row in by_level_res.all()}

    # Análises por SUB-nível (24h) — 3 níveis do prompt oficial
    by_sublevel_res = await db.execute(
        select(
            models.SupervisorAnalysis.risk_sublevel,
            func.count(models.SupervisorAnalysis.id),
        )
        .where(
            models.SupervisorAnalysis.created_at >= last_24h,
            models.SupervisorAnalysis.risk_sublevel.isnot(None),
        )
        .group_by(models.SupervisorAnalysis.risk_sublevel)
    )
    by_sublevel = {int(row[0]): row[1] for row in by_sublevel_res.all()}
    nivel1_24h = by_sublevel.get(1, 0)
    nivel2_24h = by_sublevel.get(2, 0)
    nivel3_24h = by_sublevel.get(3, 0)

    # Alertas ABERTOS por subnível (24h) — exclui dismissed/resolved
    open_by_sublevel_res = await db.execute(
        select(
            models.SupervisorAnalysis.risk_sublevel,
            func.count(func.distinct(models.SupervisorAlert.id)),
        )
        .join(
            models.SupervisorAlert,
            models.SupervisorAlert.analysis_id == models.SupervisorAnalysis.id,
        )
        .where(
            models.SupervisorAnalysis.created_at >= last_24h,
            models.SupervisorAnalysis.risk_sublevel.isnot(None),
            models.SupervisorAlert.status == "open",
        )
        .group_by(models.SupervisorAnalysis.risk_sublevel)
    )
    open_by_sublevel = {int(row[0]): row[1] for row in open_by_sublevel_res.all()}
    open_nivel1 = open_by_sublevel.get(1, 0)
    open_nivel2 = open_by_sublevel.get(2, 0)
    open_nivel3 = open_by_sublevel.get(3, 0)

    # Alertas abertos
    open_alerts_res = await db.execute(
        select(func.count(models.SupervisorAlert.id))
        .where(models.SupervisorAlert.status == "open")
    )
    open_alerts = open_alerts_res.scalar() or 0

    urgencia_alerts_res = await db.execute(
        select(func.count(models.SupervisorAlert.id))
        .where(
            models.SupervisorAlert.status == "open",
            models.SupervisorAlert.level == "URGENCIA",
        )
    )
    urgencia_alerts = urgencia_alerts_res.scalar() or 0

    atencao_alerts_res = await db.execute(
        select(func.count(models.SupervisorAlert.id))
        .where(
            models.SupervisorAlert.status == "open",
            models.SupervisorAlert.level == "ATENCAO",
        )
    )
    atencao_alerts = atencao_alerts_res.scalar() or 0

    # Users únicos em URGÊNCIA/ATENÇÃO (alerta aberto)
    users_urgencia_res = await db.execute(
        select(func.count(func.distinct(models.SupervisorAlert.user_id)))
        .where(
            models.SupervisorAlert.status == "open",
            models.SupervisorAlert.level == "URGENCIA",
        )
    )
    users_in_urgencia = users_urgencia_res.scalar() or 0

    users_atencao_res = await db.execute(
        select(func.count(func.distinct(models.SupervisorAlert.user_id)))
        .where(
            models.SupervisorAlert.status == "open",
            models.SupervisorAlert.level == "ATENCAO",
        )
    )
    users_in_atencao = users_atencao_res.scalar() or 0

    # Users em risco (pega os top 10 com alerta aberto)
    risk_users_res = await db.execute(
        select(
            models.User.id,
            models.User.email,
            models.User.full_name,
            models.User.avatar_url,
            models.SupervisorAlert.level,
            models.SupervisorAlert.id.label("alert_id"),
            models.SupervisorAlert.last_occurrence_at,
        )
        .join(models.SupervisorAlert, models.SupervisorAlert.user_id == models.User.id)
        .where(models.SupervisorAlert.status == "open")
        .order_by(
            # URGENCIA primeiro
            desc(models.SupervisorAlert.level == "URGENCIA"),
            desc(models.SupervisorAlert.last_occurrence_at),
        )
        .limit(20)
    )
    risk_users = []
    for row in risk_users_res.all():
        # Pega max score e total de mensagens nas últimas 24h desse user
        user_id = row[0]
        score_res = await db.execute(
            select(func.max(models.SupervisorAnalysis.score))
            .where(
                models.SupervisorAnalysis.user_id == user_id,
                models.SupervisorAnalysis.created_at >= last_24h,
            )
        )
        max_score = float(score_res.scalar() or 0.0)

        msgs_res = await db.execute(
            select(func.count(models.SupervisorAnalysis.id))
            .where(
                models.SupervisorAnalysis.user_id == user_id,
                models.SupervisorAnalysis.created_at >= last_24h,
            )
        )
        total_msgs = msgs_res.scalar() or 0

        # Última análise
        last_res = await db.execute(
            select(models.SupervisorAnalysis.created_at)
            .where(models.SupervisorAnalysis.user_id == user_id)
            .order_by(desc(models.SupervisorAnalysis.created_at))
            .limit(1)
        )
        last = last_res.scalar()

        risk_users.append(UserRiskInfo(
            user_id=str(user_id),
            email=row[1],
            full_name=row[2],
            avatar_url=row[3],
            current_level=row[4],
            max_score_24h=max_score,
            total_messages_24h=total_msgs,
            last_analysis_at=last.isoformat() if last else None,
            open_alert_id=str(row[5]) if row[5] else None,
        ))

    # Últimas URGÊNCIAS: só das últimas 24h + que não tenham alerta já resolvido/dismissed
    # (se for tratar de uma análise que já virou alerta e foi fechado, não aparece aqui — já vai pro histórico)
    cutoff_24h = datetime.utcnow() - timedelta(hours=24)
    recent_urgencias_res = await db.execute(
        select(
            models.SupervisorAnalysis,
            models.User.email,
            models.User.full_name,
            models.Message.content,
            models.SupervisorAlert.status,  # status do alerta relacionado (pode ser NULL)
        )
        .join(models.User, models.User.id == models.SupervisorAnalysis.user_id)
        .join(models.Message, models.Message.id == models.SupervisorAnalysis.message_id)
        .outerjoin(
            models.SupervisorAlert,
            models.SupervisorAlert.analysis_id == models.SupervisorAnalysis.id
        )
        .where(
            models.SupervisorAnalysis.level == "URGENCIA",
            models.SupervisorAnalysis.created_at >= cutoff_24h,
            # Sem alerta OU alerta ainda aberto/em análise
            (models.SupervisorAlert.id.is_(None)) | (models.SupervisorAlert.status.in_(["open", "acknowledged"])),
        )
        .order_by(desc(models.SupervisorAnalysis.created_at))
        .limit(5)
    )
    recent_urgencias = []
    for analysis, email, full_name, msg_content, alert_status in recent_urgencias_res.all():
        recent_urgencias.append({
            "analysis_id": str(analysis.id),
            "user_id": str(analysis.user_id),
            "user_email": email,
            "user_full_name": full_name,
            "level": analysis.level,
            "score": float(analysis.score),
            "reason": analysis.reason,
            "message_excerpt": (msg_content or "")[:200],
            "signals": analysis.signals or [],
            "created_at": analysis.created_at.isoformat(),
        })

    return DashboardResponse(
        counters=DashboardCounters(
            total_users=total_users,
            total_analyses_24h=total_analyses_24h,
            open_alerts=open_alerts,
            urgencia_alerts=urgencia_alerts,
            atencao_alerts=atencao_alerts,
            users_in_urgencia=users_in_urgencia,
            users_in_atencao=users_in_atencao,
            nivel1_alerts_24h=nivel1_24h,
            nivel2_alerts_24h=nivel2_24h,
            nivel3_alerts_24h=nivel3_24h,
            open_nivel1=open_nivel1,
            open_nivel2=open_nivel2,
            open_nivel3=open_nivel3,
            analyses_by_sublevel_24h=by_sublevel,
            analyses_by_level=by_level,
        ),
        high_risk_users=risk_users,
        recent_urgencias=recent_urgencias,
        generated_at=now.isoformat(),
    )


# ============================================================
# ALERTS
# ============================================================
@router.get("/alerts", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = Query(None, regex="^(open|acknowledged|resolved|dismissed)$"),
    level: Optional[str] = Query(None, regex="^(ATENCAO|URGENCIA|N1|N2|N3)$"),
    risk_sublevel: Optional[int] = Query(None, ge=1, le=3),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Lista alertas com filtros + paginação.

    Filtros:
        - status: open|acknowledged|resolved|dismissed
        - level: ATENCAO|URGENCIA (geral) OU N1|N2|N3 (subnível especifico)
        - risk_sublevel: 1|2|3 (atalho)
    """
    # Faz join pra trazer risk_sublevel do supervisor_analysis
    risk_sub_col = models.SupervisorAnalysis.risk_sublevel

    stmt = (
        select(
            models.SupervisorAlert,
            models.User.email,
            models.User.full_name,
            models.User.avatar_url,
            models.SupervisorAnalysis.message_id,
            models.SupervisorAnalysis.chat_id,
            risk_sub_col,
        )
        .join(models.User, models.User.id == models.SupervisorAlert.user_id)
        .outerjoin(models.SupervisorAnalysis, models.SupervisorAnalysis.id == models.SupervisorAlert.analysis_id)
    )

    if status:
        stmt = stmt.where(models.SupervisorAlert.status == status)
    if level:
        # Suporte pra N1/N2/N3 como atalho
        if level in ("N1", "N2", "N3"):
            sub = int(level[1])
            stmt = stmt.where(risk_sub_col == sub)
        elif level in ("ATENCAO", "URGENCIA"):
            stmt = stmt.where(models.SupervisorAlert.level == level)
    if risk_sublevel:
        stmt = stmt.where(risk_sub_col == risk_sublevel)

    # query de total ANTES do order/limit/offset
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    stmt = stmt.order_by(
        # URGENCIA primeiro, depois mais recente
        desc(models.SupervisorAlert.level == "URGENCIA"),
        desc(models.SupervisorAlert.last_occurrence_at),
    ).offset(offset).limit(limit)

    res = await db.execute(stmt)
    alerts = []
    for alert, email, full_name, avatar, msg_id, chat_id, risk_sub in res.all():
        alerts.append(AlertResponse(
            id=str(alert.id),
            user_id=str(alert.user_id),
            user_email=email,
            user_full_name=full_name,
            user_avatar_url=avatar,
            level=alert.level,
            status=alert.status,
            title=alert.title,
            message=alert.message,
            message_excerpt=alert.message_excerpt,
            message_id=str(msg_id) if msg_id else None,
            chat_id=str(chat_id) if chat_id else None,
            occurrences=alert.occurrences or 1,
            acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
            acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
            resolved_by=str(alert.resolved_by) if alert.resolved_by else None,
            resolved_at=alert.resolved_at.isoformat() if alert.resolved_at else None,
            resolution_notes=alert.resolution_notes,
            last_occurrence_at=alert.last_occurrence_at.isoformat(),
            created_at=alert.created_at.isoformat(),
            risk_sublevel=risk_sub,
            ia_confirmed=alert.ia_confirmed,
        ))
    return AlertListResponse(
        items=alerts,
        total=total,
        offset=offset,
        limit=limit,
        has_next=(offset + limit) < total,
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Marca alerta como acknowledged (visto pelo admin, mas ainda aberto)."""
    res = await db.execute(
        select(models.SupervisorAlert).where(models.SupervisorAlert.id == UUID(alert_id))
    )
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta não encontrado")

    alert.status = "acknowledged"
    alert.acknowledged_by = admin.id
    alert.acknowledged_at = datetime.utcnow()
    if payload.notes:
        alert.resolution_notes = (alert.resolution_notes or "") + f"\n[ACK] {payload.notes}"
    await db.commit()
    await db.refresh(alert)

    # Recarrega com user
    user_res = await db.execute(select(models.User).where(models.User.id == alert.user_id))
    user = user_res.scalar_one()

    return AlertResponse(
        id=str(alert.id),
        user_id=str(alert.user_id),
        user_email=user.email,
        user_full_name=user.full_name,
        user_avatar_url=user.avatar_url,
        level=alert.level,
        status=alert.status,
        title=alert.title,
        message=alert.message,
        message_excerpt=alert.message_excerpt,
        occurrences=alert.occurrences or 1,
        acknowledged_by=str(alert.acknowledged_by),
        acknowledged_at=alert.acknowledged_at.isoformat(),
        resolved_by=None,
        resolved_at=None,
        resolution_notes=alert.resolution_notes,
        last_occurrence_at=alert.last_occurrence_at.isoformat(),
        created_at=alert.created_at.isoformat(),
    )


@router.post("/alerts/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Marca alerta como resolvido."""
    res = await db.execute(
        select(models.SupervisorAlert).where(models.SupervisorAlert.id == UUID(alert_id))
    )
    alert = res.scalar_one_or_none()
    if not alert:
        raise HTTPException(404, "Alerta não encontrado")

    alert.status = "resolved"
    alert.resolved_by = admin.id
    alert.resolved_at = datetime.utcnow()
    if payload.notes:
        alert.resolution_notes = (alert.resolution_notes or "") + f"\n[RESOLVE] {payload.notes}"
    await db.commit()
    await db.refresh(alert)

    user_res = await db.execute(select(models.User).where(models.User.id == alert.user_id))
    user = user_res.scalar_one()

    return AlertResponse(
        id=str(alert.id),
        user_id=str(alert.user_id),
        user_email=user.email,
        user_full_name=user.full_name,
        user_avatar_url=user.avatar_url,
        level=alert.level,
        status=alert.status,
        title=alert.title,
        message=alert.message,
        message_excerpt=alert.message_excerpt,
        occurrences=alert.occurrences or 1,
        acknowledged_by=str(alert.acknowledged_by) if alert.acknowledged_by else None,
        acknowledged_at=alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
        resolved_by=str(alert.resolved_by),
        resolved_at=alert.resolved_at.isoformat(),
        resolution_notes=alert.resolution_notes,
        last_occurrence_at=alert.last_occurrence_at.isoformat(),
        created_at=alert.created_at.isoformat(),
    )


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertResponse)
async def dismiss_alert(
    alert_id: str,
    payload: AlertActionRequest = AlertActionRequest(),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Descarta alerta (falso positivo)."""
    return await resolve_alert(alert_id, payload, db, admin)  # mesma lógica por enquanto


# ============================================================
# USER TIMELINE + ANALYSES
# ============================================================
@router.get("/users/{user_id}/analyses", response_model=list[AnalysisResponse])
async def list_user_analyses(
    user_id: str,
    limit: int = Query(50, le=200),
    level: Optional[str] = Query(None, regex="^(NORMAL|ATENCAO|URGENCIA)$"),
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Lista análises de um user específico."""
    stmt = (
        select(models.SupervisorAnalysis, models.Message.content)
        .join(models.Message, models.Message.id == models.SupervisorAnalysis.message_id)
        .where(models.SupervisorAnalysis.user_id == UUID(user_id))
    )
    if level:
        stmt = stmt.where(models.SupervisorAnalysis.level == level)
    stmt = stmt.order_by(desc(models.SupervisorAnalysis.created_at)).limit(limit)

    res = await db.execute(stmt)
    analyses = []
    for a, msg_content in res.all():
        analyses.append(AnalysisResponse(
            id=str(a.id),
            message_id=str(a.message_id),
            user_id=str(a.user_id),
            chat_id=str(a.chat_id),
            level=a.level,
            score=float(a.score),
            reason=a.reason,
            recommended_action=a.recommended_action,
            signals=a.signals or [],
            context_used=a.context_used or {},
            model_used=a.model_used,
            analysis_duration_ms=a.analysis_duration_ms,
            created_at=a.created_at.isoformat(),
            message_excerpt=(msg_content or "")[:300] if msg_content else None,
        ))
    return analyses


@router.get("/users/{user_id}/timeline", response_model=dict)
async def get_user_timeline(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin),
):
    """Histórico consolidado de um user: contadores, evolução, últimas análises, alertas."""
    user_res = await db.execute(select(models.User).where(models.User.id == UUID(user_id)))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User não encontrado")

    # Contadores totais
    counts_res = await db.execute(
        select(
            models.SupervisorAnalysis.level,
            func.count(models.SupervisorAnalysis.id),
        )
        .where(models.SupervisorAnalysis.user_id == user.id)
        .group_by(models.SupervisorAnalysis.level)
    )
    by_level = {row[0]: row[1] for row in counts_res.all()}

    # Última análise
    last_res = await db.execute(
        select(models.SupervisorAnalysis)
        .where(models.SupervisorAnalysis.user_id == user.id)
        .order_by(desc(models.SupervisorAnalysis.created_at))
        .limit(1)
    )
    last = last_res.scalar_one_or_none()

    # Alertas abertos
    alerts_res = await db.execute(
        select(models.SupervisorAlert)
        .where(
            models.SupervisorAlert.user_id == user.id,
            models.SupervisorAlert.status.in_(["open", "acknowledged"]),
        )
        .order_by(desc(models.SupervisorAlert.created_at))
    )
    open_alerts = [
        {
            "id": str(a.id),
            "level": a.level,
            "title": a.title,
            "status": a.status,
            "occurrences": a.occurrences or 1,
            "created_at": a.created_at.isoformat(),
            "last_occurrence_at": a.last_occurrence_at.isoformat(),
        }
        for a in alerts_res.scalars().all()
    ]

    # Resumo dos últimos 7 dias
    last_7d = datetime.utcnow() - timedelta(days=7)
    daily_res = await db.execute(
        select(models.SupervisorDailySummary)
        .where(
            models.SupervisorDailySummary.user_id == user.id,
            models.SupervisorDailySummary.summary_date >= (datetime.utcnow() - timedelta(days=7)).date(),
        )
        .order_by(desc(models.SupervisorDailySummary.summary_date))
    )
    daily = [
        {
            "date": d.summary_date.isoformat(),
            "total": d.total_messages,
            "normal": d.normal_count,
            "atencao": d.atencao_count,
            "urgencia": d.urgencia_count,
            "max_score": float(d.max_score or 0),
        }
        for d in daily_res.scalars().all()
    ]

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "full_name": user.full_name,
            "avatar_url": user.avatar_url,
        },
        "totals_by_level": by_level,
        "last_analysis": {
            "level": last.level,
            "score": float(last.score) if last else 0.0,
            "reason": last.reason if last else None,
            "created_at": last.created_at.isoformat() if last else None,
        } if last else None,
        "open_alerts": open_alerts,
        "daily_history": daily,
    }
