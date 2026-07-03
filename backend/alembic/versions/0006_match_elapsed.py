"""matches.elapsed: minuto de juego en vivo

API-Football envía el minuto transcurrido en status.elapsed. Se persiste para
mostrar el minuto en (casi) tiempo real en la UI. Nullable: solo tiene valor
durante el partido (None en los programados; en los finalizados no se muestra).

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("matches", sa.Column("elapsed", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("matches", "elapsed")
