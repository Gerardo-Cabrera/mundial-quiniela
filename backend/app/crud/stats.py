from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.match import Match, MatchStatus
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.stats import FirstGoalMatch, ScoreCount, StatsSummary, UserCount


def _ranking(counts: dict[str, int]) -> list[UserCount]:
    """Ranking desc por nº de aciertos (desempate alfabético); omite a quien no acertó."""
    return sorted(
        (UserCount(team_name=t, count=c) for t, c in counts.items() if c > 0),
        key=lambda u: (-u.count, u.team_name),
    )


class StatsCRUD:
    async def get_summary(self, db: AsyncSession) -> StatsSummary:
        """Aciertos de primer gol (por partido + ranking) y de marcador exacto (marcador
        real más repetido + ranking). Solo cuenta predicciones ya calculadas de partidos
        finalizados. Dos consultas acotadas + agregación en Python (cross-DB, como en
        matchday); no hay N+1."""
        matches = (await db.execute(
            select(
                Match.id, Match.home_team, Match.away_team, Match.match_date,
                Match.home_score, Match.away_score,
                Match.first_goal_player_id, Match.first_goal_player,
            )
            .where(Match.status == MatchStatus.FINISHED)
            .order_by(Match.match_date.desc(), Match.id.desc())
        )).all()

        preds = (await db.execute(
            select(
                User.team_name, Prediction.match_id,
                Prediction.predicted_home, Prediction.predicted_away,
                Prediction.first_goal_player_id,
            )
            .select_from(Prediction).join(Match).join(User)
            .where(Prediction.is_calculated.is_(True))
        )).all()

        by_id = {m.id: m for m in matches}
        exact_counts: dict[str, int] = defaultdict(int)
        fg_counts: dict[str, int] = defaultdict(int)
        fg_hitters: dict[int, list[str]] = defaultdict(list)  # match_id -> equipos
        for team, match_id, ph, pa, pfg in preds:
            m = by_id.get(match_id)
            if m is None or m.home_score is None or m.away_score is None:
                continue
            if ph == m.home_score and pa == m.away_score:
                exact_counts[team] += 1
            # Primer gol por jugador (id), igual que el scoring: ambos deben existir.
            if pfg is not None and m.first_goal_player_id is not None and pfg == m.first_goal_player_id:
                fg_counts[team] += 1
                fg_hitters[match_id].append(team)

        # Marcador real más repetido (sobre los partidos finalizados; empates → varios).
        score_freq: dict[str, int] = defaultdict(int)
        for m in matches:
            if m.home_score is not None and m.away_score is not None:
                score_freq[f"{m.home_score}-{m.away_score}"] += 1
        top = max(score_freq.values(), default=0)
        top_scores = sorted(
            (ScoreCount(score=s, count=c) for s, c in score_freq.items() if c == top and top > 0),
            key=lambda x: x.score,
        )

        first_goal_matches = [
            FirstGoalMatch(
                match_id=m.id, home_team=m.home_team, away_team=m.away_team,
                match_date=m.match_date, scorer=m.first_goal_player,
                hitters=sorted(fg_hitters.get(m.id, [])),
            )
            for m in matches if m.first_goal_player_id is not None
        ]

        return StatsSummary(
            first_goal_matches=first_goal_matches,
            first_goal_ranking=_ranking(fg_counts),
            top_scores=top_scores,
            exact_ranking=_ranking(exact_counts),
        )


stats_crud = StatsCRUD()
