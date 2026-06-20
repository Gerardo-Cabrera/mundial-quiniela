"""Añade la tabla teams (selecciones del Mundial) y retira una tabla no usada

- `teams`: selecciones del Mundial sincronizadas desde API-Football. Se usan al
  registrar los pronósticos de cada jornada y como catálogo de equipos.
- Se elimina la tabla `top8_picks`, que no se utiliza en esta aplicación.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("api_team_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("code", sa.String(length=10), nullable=True),
        sa.Column("country", sa.String(length=100), nullable=True),
        sa.Column("logo", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_teams_id"), "teams", ["id"])
    op.create_index(op.f("ix_teams_api_team_id"), "teams", ["api_team_id"], unique=True)
    op.create_index(op.f("ix_teams_name"), "teams", ["name"], unique=True)

    op.drop_table("top8_picks")


def downgrade() -> None:
    op.create_table(
        "top8_picks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("team_name", sa.String(length=100), nullable=False),
        sa.Column("points_earned", sa.Integer(), nullable=False),
        sa.Column("is_calculated", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "position", name="uq_top8_user_position"),
        sa.UniqueConstraint("user_id", "team_name", name="uq_top8_user_team"),
    )
    op.create_index(op.f("ix_top8_picks_id"), "top8_picks", ["id"])
    op.create_index(op.f("ix_top8_picks_user_id"), "top8_picks", ["user_id"])

    op.drop_index(op.f("ix_teams_name"), table_name="teams")
    op.drop_index(op.f("ix_teams_api_team_id"), table_name="teams")
    op.drop_index(op.f("ix_teams_id"), table_name="teams")
    op.drop_table("teams")
