from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.user import User
from app.schemas import LeaderboardEntry
from app.core.deps import get_current_user
from app.crud import leaderboard_crud

router = APIRouter(prefix="/leaderboard", tags=["Leaderboard"])


@router.get("/", response_model=list[LeaderboardEntry])
async def get_leaderboard(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return await leaderboard_crud.get_leaderboard(db)
