from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.user import User
from app.schemas.matchday import MatchdaysSummary
from app.core.deps import get_current_user
from app.crud import matchday_crud

router = APIRouter(prefix="/matchdays", tags=["Matchdays"])

_TOURNAMENT_TZ = ZoneInfo(settings.TOURNAMENT_TZ)


@router.get("/", response_model=MatchdaysSummary)
async def get_matchdays_summary(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resumen por jornada (día): puntos de cada participante y el MVP del día, más
    el ranking de MVPs (veces como MVP). Alimenta las vistas Jornada y MVPs."""
    return await matchday_crud.get_summary(db, _TOURNAMENT_TZ)
