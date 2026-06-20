"""Añade la tabla participant_teams (equipos de los jugadores) y la siembra

Los 16 equipos de la quiniela (con los que se registran los participantes)
dejan de estar hardcodeados en el código: pasan a la BD. Esta migración crea la
tabla y la siembra con la lista canónica. La validación del registro y el
endpoint `GET /config/teams` leen desde aquí.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

# Lista canónica de los equipos de los participantes (seed inicial). Self-contained
# a propósito: una migración es un snapshot histórico y no debe depender del código
# de la app, que puede cambiar. Para altas/bajas posteriores: editar la tabla.
PARTICIPANT_TEAMS = [
    "Jax FC",
    "Genkidama F.C",
    "Jihyo F.C",
    "Rojos Del Ávila",
    "Fiebruos C.F",
    "Dragon Lord F.C",
    "Super Marihuana nos Blue F.C",
    "Rostyn Saca Las Actas F.C",
    "Super Saiyans C.F",
    "Megalink FC",
    "Caramelo De Chocolate FC",
    "Jack F.C",
    "Mugion ce FC",
    "Soldier Boy",
    "Petare F.C",
    "Choupa-Mesta Draco FC",
]


def upgrade() -> None:
    participant_teams = op.create_table(
        "participant_teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_participant_teams_id"), "participant_teams", ["id"])
    op.create_index(op.f("ix_participant_teams_name"), "participant_teams", ["name"], unique=True)

    op.bulk_insert(participant_teams, [{"name": name} for name in PARTICIPANT_TEAMS])


def downgrade() -> None:
    op.drop_index(op.f("ix_participant_teams_name"), table_name="participant_teams")
    op.drop_index(op.f("ix_participant_teams_id"), table_name="participant_teams")
    op.drop_table("participant_teams")
