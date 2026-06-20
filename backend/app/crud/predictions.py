from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.models.prediction import Prediction


class PredictionCRUD:
    async def get_by_user(self, db: AsyncSession, user_id: int) -> list[Prediction]:
        result = await db.execute(
            select(Prediction)
            .where(Prediction.user_id == user_id)
            .options(selectinload(Prediction.match))
            .order_by(Prediction.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_match(
        self, db: AsyncSession, user_id: int, match_id: int
    ) -> Prediction | None:
        result = await db.execute(
            select(Prediction).where(
                Prediction.user_id == user_id,
                Prediction.match_id == match_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, db: AsyncSession, prediction_id: int, user_id: int
    ) -> Prediction | None:
        result = await db.execute(
            select(Prediction).where(
                Prediction.id == prediction_id,
                Prediction.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        match_id: int,
        predicted_home: int,
        predicted_away: int,
        first_goal_player_id: int | None = None,
        first_goal_player: str | None = None,
    ) -> Prediction:
        prediction = Prediction(
            user_id=user_id,
            match_id=match_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            first_goal_player_id=first_goal_player_id,
            first_goal_player=first_goal_player,
        )
        db.add(prediction)
        await db.flush()
        await db.refresh(prediction, attribute_names=["match"])
        return prediction

    async def update(
        self,
        db: AsyncSession,
        prediction: Prediction,
        *,
        predicted_home: int,
        predicted_away: int,
        first_goal_player_id: int | None = None,
        first_goal_player: str | None = None,
    ) -> Prediction:
        prediction.predicted_home = predicted_home
        prediction.predicted_away = predicted_away
        prediction.first_goal_player_id = first_goal_player_id
        prediction.first_goal_player = first_goal_player
        prediction.is_calculated = False
        prediction.points_earned = 0
        await db.flush()
        await db.refresh(prediction, attribute_names=["match"])
        return prediction

    async def upsert(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        match_id: int,
        predicted_home: int,
        predicted_away: int,
        first_goal_player_id: int | None = None,
        first_goal_player: str | None = None,
    ) -> Prediction:
        """Crea o actualiza la predicción de (usuario, partido). Idempotente
        gracias a la constraint UNIQUE(user_id, match_id)."""
        existing = await self.get_by_user_and_match(db, user_id, match_id)
        if existing:
            return await self.update(
                db, existing,
                predicted_home=predicted_home,
                predicted_away=predicted_away,
                first_goal_player_id=first_goal_player_id,
                first_goal_player=first_goal_player,
            )
        return await self.create(
            db,
            user_id=user_id,
            match_id=match_id,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            first_goal_player_id=first_goal_player_id,
            first_goal_player=first_goal_player,
        )

    async def delete(self, db: AsyncSession, prediction: Prediction) -> None:
        await db.delete(prediction)


prediction_crud = PredictionCRUD()
