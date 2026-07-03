from app.routers.auth import router as auth_router
from app.routers.matches import router as matches_router
from app.routers.predictions import router as predictions_router
from app.routers.leaderboard import router as leaderboard_router
from app.routers.matchdays import router as matchdays_router
from app.routers.stats import router as stats_router
from app.routers.config import router as config_router

__all__ = [
    "auth_router",
    "matches_router",
    "predictions_router",
    "leaderboard_router",
    "matchdays_router",
    "stats_router",
    "config_router",
]
