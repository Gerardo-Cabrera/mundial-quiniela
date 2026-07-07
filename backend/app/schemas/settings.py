from pydantic import BaseModel


class SettingsOut(BaseModel):
    late_predictions_enabled: bool

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    late_predictions_enabled: bool
