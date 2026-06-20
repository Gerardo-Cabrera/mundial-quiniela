"""
Unit tests para el motor de puntuación Mundial Quiniela.
Cubre: resultado exacto, victoria/empate, primer gol, fases grupos vs knockout.
"""
import pytest
from app.models.match import MatchPhase
from app.services.scoring import (
    calculate_match_points,
    GROUP_POINTS,
    KNOCKOUT_POINTS,
    _get_outcome,
)


# ── HELPERS ───────────────────────────────────────────────────────────────────


class TestGetOutcome:
    def test_home_win(self):
        assert _get_outcome(3, 1) == "home"

    def test_away_win(self):
        assert _get_outcome(0, 2) == "away"

    def test_draw(self):
        assert _get_outcome(1, 1) == "draw"

    def test_draw_zero(self):
        assert _get_outcome(0, 0) == "draw"


# ── GROUP PHASE SCORING ────────────────────────────────────────────────────


class TestGroupScoring:
    """Tests para la fase de grupos (group stage)."""

    def _calc(self, **kwargs):
        defaults = {
            "predicted_home": 0,
            "predicted_away": 0,
            "predicted_first_goal_player_id": None,
            "actual_home": 0,
            "actual_away": 0,
            "actual_first_goal_player_id": None,
            "phase": MatchPhase.GROUP_STAGE,
        }
        defaults.update(kwargs)
        return calculate_match_points(**defaults)

    def test_exact_score(self):
        """Resultado exacto (victoria): exacto + victoria se SUMAN."""
        r = self._calc(
            predicted_home=2, predicted_away=1,
            actual_home=2, actual_away=1,
        )
        assert r["exact"] == GROUP_POINTS["exact"]
        assert r["outcome"] == GROUP_POINTS["win"]
        assert r["total"] == GROUP_POINTS["exact"] + GROUP_POINTS["win"]

    def test_exact_draw(self):
        """Empate exacto: exacto + empate se SUMAN."""
        r = self._calc(
            predicted_home=1, predicted_away=1,
            actual_home=1, actual_away=1,
        )
        assert r["exact"] == GROUP_POINTS["exact"]
        assert r["outcome"] == GROUP_POINTS["draw"]
        assert r["total"] == GROUP_POINTS["exact"] + GROUP_POINTS["draw"]

    def test_correct_winner_wrong_score(self):
        """Acierta ganador, falla marcador: 5 pts."""
        r = self._calc(
            predicted_home=3, predicted_away=0,
            actual_home=2, actual_away=1,
        )
        assert r["exact"] == 0
        assert r["outcome"] == GROUP_POINTS["win"]
        assert r["total"] == GROUP_POINTS["win"]

    def test_correct_draw_wrong_score(self):
        """Acierta empate, falla marcador: 6 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=2,
            actual_home=0, actual_away=0,
        )
        assert r["exact"] == 0
        assert r["outcome"] == GROUP_POINTS["draw"]
        assert r["total"] == GROUP_POINTS["draw"]

    def test_wrong_outcome(self):
        """Falla resultado completamente: 0 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            actual_home=0, actual_away=3,
        )
        assert r["total"] == 0

    def test_first_goal_correct(self):
        """Primer goleador correcto (mismo id): +3 pts."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            predicted_first_goal_player_id=10,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == GROUP_POINTS["first_goal"]
        assert r["total"] == GROUP_POINTS["win"] + GROUP_POINTS["first_goal"]

    def test_first_goal_wrong(self):
        """Primer goleador incorrecto (id distinto): 0 pts de primer gol."""
        r = self._calc(
            predicted_home=2, predicted_away=0,
            predicted_first_goal_player_id=11,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == 0

    def test_first_goal_none_predicted(self):
        """Sin predicción de primer goleador: no suma."""
        r = self._calc(
            predicted_home=1, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=0,
            actual_first_goal_player_id=10,
        )
        assert r["first_goal"] == 0

    def test_first_goal_none_actual(self):
        """Sin primer goleador real (e.g. 0-0): no suma."""
        r = self._calc(
            predicted_home=0, predicted_away=0,
            predicted_first_goal_player_id=11,
            actual_home=0, actual_away=0,
            actual_first_goal_player_id=None,
        )
        assert r["first_goal"] == 0

    def test_exact_plus_first_goal(self):
        """Máximo en grupos: exacto + victoria + primer goleador (todo suma)."""
        r = self._calc(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=22,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=22,
        )
        assert r["total"] == GROUP_POINTS["exact"] + GROUP_POINTS["win"] + GROUP_POINTS["first_goal"]

    def test_exact_and_outcome_are_additive(self):
        """Exacto y victoria/empate se SUMAN (no se excluyen)."""
        r = self._calc(
            predicted_home=3, predicted_away=1,
            actual_home=3, actual_away=1,
        )
        assert r["exact"] == GROUP_POINTS["exact"]
        assert r["outcome"] == GROUP_POINTS["win"]
        assert r["total"] == GROUP_POINTS["exact"] + GROUP_POINTS["win"]


# ── KNOCKOUT PHASE SCORING ───────────────────────────────────────────────────


class TestKnockoutScoring:
    """Tests para fases eliminatorias (knockout)."""

    @pytest.mark.parametrize("phase", [
        MatchPhase.ROUND_OF_32,
        MatchPhase.ROUND_OF_16,
        MatchPhase.QUARTER_FINALS,
        MatchPhase.SEMI_FINALS,
        MatchPhase.FINAL,
    ])
    def test_exact_score_knockout(self, phase):
        r = calculate_match_points(
            predicted_home=1, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=0,
            actual_first_goal_player_id=None,
            phase=phase,
        )
        assert r["exact"] == KNOCKOUT_POINTS["exact"]
        assert r["total"] == KNOCKOUT_POINTS["exact"] + KNOCKOUT_POINTS["win"]

    def test_correct_winner_knockout(self):
        r = calculate_match_points(
            predicted_home=3, predicted_away=0,
            predicted_first_goal_player_id=None,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=None,
            phase=MatchPhase.FINAL,
        )
        assert r["outcome"] == KNOCKOUT_POINTS["win"]

    def test_correct_draw_knockout(self):
        r = calculate_match_points(
            predicted_home=2, predicted_away=2,
            predicted_first_goal_player_id=None,
            actual_home=1, actual_away=1,
            actual_first_goal_player_id=None,
            phase=MatchPhase.QUARTER_FINALS,
        )
        assert r["outcome"] == KNOCKOUT_POINTS["draw"]

    def test_first_goal_knockout(self):
        r = calculate_match_points(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=33,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=33,
            phase=MatchPhase.SEMI_FINALS,
        )
        assert r["first_goal"] == KNOCKOUT_POINTS["first_goal"]
        assert r["total"] == (
            KNOCKOUT_POINTS["exact"] + KNOCKOUT_POINTS["win"] + KNOCKOUT_POINTS["first_goal"]
        )

    def test_max_knockout_points(self):
        """Máximo en la final: exacto 11 + victoria 8 + primer goleador 5 = 24."""
        r = calculate_match_points(
            predicted_home=2, predicted_away=1,
            predicted_first_goal_player_id=44,
            actual_home=2, actual_away=1,
            actual_first_goal_player_id=44,
            phase=MatchPhase.FINAL,
        )
        assert r["total"] == (
            KNOCKOUT_POINTS["exact"] + KNOCKOUT_POINTS["win"] + KNOCKOUT_POINTS["first_goal"]
        )
        assert r["total"] == 24
