from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.match import MatchPhase, MatchStatus
from app.models.user import User
from app.schemas import MatchOut, PlayerOut
from app.core.deps import get_current_user, get_admin_user
from app.core.rate_limit import limiter
from app.services.scheduler import sync_fixtures
from app.crud import match_crud, player_crud

router = APIRouter(prefix="/matches", tags=["Matches"])


@router.get("/", response_model=list[MatchOut])
async def get_matches(
    phase: MatchPhase | None = None,
    status: MatchStatus | None = None,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await match_crud.get_all(db, phase=phase, status=status)


@router.get("/{match_id}", response_model=MatchOut)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    match = await match_crud.get_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    return match


@router.get("/{match_id}/players", response_model=list[PlayerOut])
async def get_match_players(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Plantillas de los dos equipos del partido, para elegir el primer goleador.
    Vacío si aún no se han sincronizado las plantillas (depende del plan de API)."""
    match = await match_crud.get_by_id(db, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    return await player_crud.get_for_teams(db, [match.home_team, match.away_team])


@router.post("/sync", status_code=202, summary="Admin: Forzar sync con API-Football")
@limiter.limit(settings.RATE_LIMIT_SYNC)
async def force_sync(
    request: Request,  # obligatorio para que slowapi resuelva la IP
    background_tasks: BackgroundTasks,
    _: User = Depends(get_admin_user),
):
    """Endpoint admin para forzar sincronización manual (en background)."""
    background_tasks.add_task(sync_fixtures)
    return {"message": "Sincronización iniciada."}
