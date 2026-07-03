from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas.stats import StatsSummary
from app.core.deps import get_current_user
from app.crud import stats_crud

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("/", response_model=StatsSummary)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Aciertos de primer gol (por partido + ranking) y de marcador exacto (marcador
    real más repetido + ranking). Alimenta la vista Aciertos."""
    return await stats_crud.get_summary(db)
