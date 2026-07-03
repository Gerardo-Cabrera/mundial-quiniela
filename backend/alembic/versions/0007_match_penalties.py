"""matches.penalty_home/away: definición por penales

En eliminatorias empatadas, API-Football entrega la tanda en score.penalty. Se
persiste para mostrar cómo quedó la definición en la tarjeta de Resultados. Nullable:
solo tiene valor cuando el partido se definió por penales.

Revision ID: 0007
Revises: 0006
Create Date: 2026-07-03
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("penalty_home", sa.Integer(), nullable=True))
    op.add_column("matches", sa.Column("penalty_away", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "penalty_away")
    op.drop_column("matches", "penalty_home")
