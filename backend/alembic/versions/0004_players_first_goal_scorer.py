"""Primer gol por JUGADOR (primer goleador): tabla players y columnas de goleador

El pronóstico del primer gol pasa de ser por EQUIPO a por JUGADOR:
- nueva tabla `players` (plantillas sincronizadas desde API-Football),
- `predictions`: se reemplaza `first_goal_team` por `first_goal_player_id` +
  `first_goal_player`,
- `matches`: se añaden `first_goal_player_id` + `first_goal_player` (el goleador
  real); se conserva `first_goal_team` (equipo del goleador, informativo).

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-18
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- players ---
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_player_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("team_api_id", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("position", sa.String(length=30), nullable=True),
        sa.Column("photo", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_players_id"), "players", ["id"])
    op.create_index(op.f("ix_players_api_player_id"), "players", ["api_player_id"], unique=True)
    op.create_index(op.f("ix_players_team_api_id"), "players", ["team_api_id"])
    op.create_index(op.f("ix_players_team_name"), "players", ["team_name"])

    # --- matches: goleador real (se conserva first_goal_team) ---
    op.add_column("matches", sa.Column("first_goal_player_id", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("first_goal_player", sa.String(length=100), nullable=True))

    # --- predictions: primer gol por jugador en vez de por equipo ---
    op.add_column("predictions", sa.Column("first_goal_player_id", sa.Integer(), nullable=True))
    op.add_column("predictions", sa.Column("first_goal_player", sa.String(length=100), nullable=True))
    op.drop_column("predictions", "first_goal_team")


def downgrade() -> None:
    op.add_column("predictions", sa.Column("first_goal_team", sa.String(length=100), nullable=True))
    op.drop_column("predictions", "first_goal_player")
    op.drop_column("predictions", "first_goal_player_id")

    op.drop_column("matches", "first_goal_player")
    op.drop_column("matches", "first_goal_player_id")

    op.drop_index(op.f("ix_players_team_name"), table_name="players")
    op.drop_index(op.f("ix_players_team_api_id"), table_name="players")
    op.drop_index(op.f("ix_players_api_player_id"), table_name="players")
    op.drop_index(op.f("ix_players_id"), table_name="players")
    op.drop_table("players")
