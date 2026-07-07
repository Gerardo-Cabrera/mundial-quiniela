from sqlalchemy import Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class AppSetting(Base):
    """Ajustes globales de la app en una **fila única** (id=1). Hoy solo el
    interruptor de pronósticos tardíos; se lee/crea vía setting_crud."""
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    # Interruptor admin: permite pronosticar en la ventana entre el cierre normal
    # (1 h antes) y el inicio del primer partido del día (nunca tras el inicio).
    late_predictions_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
