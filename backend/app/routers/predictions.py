from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.database import get_db
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas import PredictionCreate, PredictionOut, PredictionBackfillRequest
from app.core.deps import get_current_user, get_admin_user
from app.crud import prediction_crud, match_crud, user_crud, player_crud
from app.services.scheduler import sync_first_goals, calculate_pending_points

router = APIRouter(prefix="/predictions", tags=["Predictions"])

_TOURNAMENT_TZ = ZoneInfo(settings.TOURNAMENT_TZ)


async def _ensure_match_predictable(db: AsyncSession, match: Match) -> None:
    """Los pronósticos de una jornada cierran **1 hora antes del primer partido
    del día** (no por partido individual): así nadie puede esperar a ver el primer
    partido para pronosticar los siguientes del mismo día. (El backfill admin
    omite esta validación para cargar jornadas ya jugadas.)"""
    first_kickoff = await match_crud.get_day_first_kickoff(db, match.match_date, _TOURNAMENT_TZ)
    if datetime.now(timezone.utc) >= first_kickoff - timedelta(hours=1):
        raise HTTPException(
            status_code=400,
            detail="Los pronósticos de esta jornada ya cerraron (1 hora antes del primer partido del día).",
        )


async def _validate_first_goal_player(
    db: AsyncSession, match: Match, player_id: int | None
) -> tuple[int | None, str | None]:
    """Valida el pronóstico de primer goleador: el jugador debe existir y jugar
    en uno de los dos equipos del partido. Devuelve (api_player_id, nombre) para
    persistir, o (None, None) si no se pronostica."""
    if player_id is None:
        return None, None
    player = await player_crud.get_by_api_id(db, player_id)
    if player is None or player.team_name not in (match.home_team, match.away_team):
        raise HTTPException(
            status_code=400,
            detail=f"El jugador {player_id} no pertenece a {match.home_team} ni {match.away_team}.",
        )
    return player.api_player_id, player.name


@router.get("/", response_model=list[PredictionOut])
async def get_my_predictions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await prediction_crud.get_by_user(db, current_user.id)


@router.post("/", response_model=PredictionOut, status_code=201)
async def create_or_update_prediction(
    data: PredictionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    match = await match_crud.get_by_id(db, data.match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Partido no encontrado.")
    await _ensure_match_predictable(db, match)
    fg_player_id, fg_player_name = await _validate_first_goal_player(
        db, match, data.first_goal_player_id
    )

    return await prediction_crud.upsert(
        db,
        user_id=current_user.id,
        match_id=data.match_id,
        predicted_home=data.predicted_home,
        predicted_away=data.predicted_away,
        first_goal_player_id=fg_player_id,
        first_goal_player=fg_player_name,
    )


@router.delete("/{prediction_id}", status_code=204)
async def delete_prediction(
    prediction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    prediction = await prediction_crud.get_by_id_and_user(db, prediction_id, current_user.id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Predicción no encontrada.")
    if prediction.is_calculated:
        raise HTTPException(status_code=400, detail="No se puede eliminar una predicción ya calculada.")
    await prediction_crud.delete(db, prediction)


@router.post(
    "/admin/backfill",
    response_model=list[PredictionOut],
    status_code=201,
    summary="Admin: Cargar pronósticos de partidos ya jugados",
)
async def backfill_predictions(
    data: PredictionBackfillRequest,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_admin_user),
):
    """
    Carga los pronósticos de un participante para partidos que ya comenzaron o
    finalizaron (el torneo arrancó el 11/06 y los pronósticos se hicieron antes
    del kickoff). A diferencia del endpoint normal, NO aplica la validación de
    fecha: por eso es exclusivo de admin. Crea o actualiza por (usuario, partido);
    idempotente.

    Si alguno de los partidos **ya finalizó**, dispara el mismo pipeline del
    scheduler (resolver el **primer gol** real + **calcular puntos**) para puntuar
    al instante, sin esperar al timer de respaldo de 30 min.
    """
    user = await user_crud.get_by_team(db, data.team_name)
    if not user:
        raise HTTPException(status_code=404, detail=f"Participante '{data.team_name}' no encontrado.")

    saved: list[Prediction] = []
    any_finished = False
    for item in data.predictions:
        match = await match_crud.get_by_id(db, item.match_id)
        if not match:
            raise HTTPException(status_code=404, detail=f"Partido {item.match_id} no encontrado.")
        if match.status == MatchStatus.FINISHED:
            any_finished = True
        fg_player_id, fg_player_name = await _validate_first_goal_player(
            db, match, item.first_goal_player_id
        )

        prediction = await prediction_crud.upsert(
            db,
            user_id=user.id,
            match_id=item.match_id,
            predicted_home=item.predicted_home,
            predicted_away=item.predicted_away,
            first_goal_player_id=fg_player_id,
            first_goal_player=fg_player_name,
        )
        saved.append(prediction)

    if any_finished:
        # Los jobs abren su propia sesión y solo ven lo confirmado: commit antes.
        await db.commit()
        # Mismo orden que el pipeline del scheduler: primer gol → puntos. Ambos
        # van envueltos en _retry (toleran fallos de red; los timers son respaldo).
        await sync_first_goals()
        await calculate_pending_points()
        # Refrescar para devolver el estado ya puntuado (los jobs escribieron en
        # otra sesión): puntos/cálculo de la predicción y primer gol real del partido.
        for pred in saved:
            await db.refresh(pred)
            await db.refresh(pred.match)
    return saved
