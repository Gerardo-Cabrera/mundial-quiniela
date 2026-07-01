from datetime import date
from pydantic import BaseModel


class MatchdayUserPoints(BaseModel):
    user_id: int
    team_name: str
    points: int


class MatchdayEntry(BaseModel):
    date: date
    # Participantes con predicción ya calculada ese día, ordenados por puntos (desc).
    entries: list[MatchdayUserPoints]
    mvp_points: int          # puntos del MVP (0 si nadie puntuó ese día)
    mvps: list[str]          # equipo(s) con más puntos (>0); vacío si mvp_points == 0


class MvpRankEntry(BaseModel):
    team_name: str
    count: int               # veces que fue MVP de una jornada


class MatchdaysSummary(BaseModel):
    days: list[MatchdayEntry]        # cronológico ascendente
    mvp_ranking: list[MvpRankEntry]  # desc por count, desempate alfabético
