"""users.must_change_password: forzar cambio de contraseña en el primer ingreso

Las cuentas de los participantes se crean por script con una contraseña inicial
compartida ("12345678"). Esta columna las marca para obligar al usuario a cambiarla
en su primer inicio de sesión. server_default=false: las filas existentes (p. ej. el
admin) quedan en false y no se ven forzadas.

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-29
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "must_change_password",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
