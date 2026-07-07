from sqlalchemy.ext.asyncio import AsyncSession
from app.models.setting import AppSetting


class SettingCRUD:
    async def get(self, db: AsyncSession) -> AppSetting:
        """Ajustes globales (fila única id=1); la crea con valores por defecto si aún
        no existe, para no depender de un seed."""
        setting = await db.get(AppSetting, 1)
        if setting is None:
            setting = AppSetting(id=1)
            db.add(setting)
            await db.flush()
        return setting

    async def set_late_predictions(self, db: AsyncSession, enabled: bool) -> AppSetting:
        setting = await self.get(db)
        setting.late_predictions_enabled = enabled
        await db.flush()
        return setting


setting_crud = SettingCRUD()
