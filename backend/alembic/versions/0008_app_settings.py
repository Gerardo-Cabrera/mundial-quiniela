"""app_settings: ajustes globales (interruptor de pronósticos tardíos)

Fila única (id=1) con el interruptor admin que permite pronosticar en la ventana
entre el cierre normal (1 h antes) y el inicio del primer partido del día. La fila se
crea al vuelo (setting_crud) si no existe; aquí solo se crea la tabla.

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-07
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "late_predictions_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("app_settings")
