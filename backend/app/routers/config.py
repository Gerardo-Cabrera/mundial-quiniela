from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.crud import team_crud, participant_team_crud, setting_crud
from app.core.deps import get_admin_user, get_current_user
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.settings import SettingsOut, SettingsUpdate
from app.services.scheduler import sync_teams

router = APIRouter(prefix="/config", tags=["Config"])


@router.get("/teams")
async def get_teams(db: AsyncSession = Depends(get_db)):
    """Equipos de la quiniela (participantes) y selecciones del Mundial.

    Ambas listas se leen de la BD: los participantes (tabla `participant_teams`)
    y las selecciones (tabla `teams`, sincronizadas desde API-Football, usadas en
    los pronósticos de cada jornada). Público, sin auth."""
    return {
        "allowed_teams": await participant_team_crud.get_all_names(db),
        "wc_teams": await team_crud.get_all_names(db),
    }


@router.post("/teams/sync", status_code=202, summary="Admin: Forzar sync de selecciones")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync_teams(
    request: Request,  # obligatorio para que slowapi resuelva la IP
    background_tasks: BackgroundTasks,
    _: User = Depends(get_admin_user),
):
    """Sincroniza manualmente las selecciones del Mundial desde API-Football."""
    background_tasks.add_task(sync_teams)
    return {"message": "Sincronización de selecciones iniciada."}


@router.get("/settings", response_model=SettingsOut)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Ajustes globales. `late_predictions_enabled` lo usa el frontend para reabrir la
    edición en la ventana de pronósticos tardíos."""
    return await setting_crud.get(db)


@router.post("/settings", response_model=SettingsOut, summary="Admin: Interruptor de pronósticos tardíos")
async def update_settings(
    data: SettingsUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """Activa/desactiva los **pronósticos tardíos**: con `true`, se puede pronosticar
    hasta el inicio del primer partido del día (no solo hasta 1 h antes); nunca tras el
    inicio."""
    return await setting_crud.set_late_predictions(db, data.late_predictions_enabled)
