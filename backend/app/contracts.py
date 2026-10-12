from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class Telemetry(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    schema_version: Literal[1]
    message_id: UUID
    device_id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{0,47}$')
    experiment_id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{0,47}$')
    unit_id: str = Field(pattern=r'^[a-z0-9][a-z0-9-]{0,47}$')
    treatment: Literal['T1', 'T2', 'T3']
    source: Literal['simulation', 'physical']
    collected_at: AwareDatetime
    calibration_id: str = Field(min_length=1, max_length=80)
    soil_raw: int = Field(ge=0, le=4095, strict=True)
    soil_index: float | None = Field(default=None, ge=0, le=100)
    sensor_valid: bool = Field(strict=True)
    temperature_c: float | None = Field(default=None, ge=-40, le=85)
    humidity_pct: float | None = Field(default=None, ge=0, le=100)
    reservoir_mass_g: float | None = Field(default=None, ge=0)
    pump_voltage_v: float | None = Field(default=None, ge=0, le=26)
    pump_current_a: float | None = Field(default=None, ge=0)

    @model_validator(mode='after')
    def consistency(self):
        if self.collected_at > datetime.now(timezone.utc) + timedelta(minutes=5):
            raise ValueError('collected_at está mais de cinco minutos no futuro')
        if self.sensor_valid and self.soil_index is None:
            raise ValueError('sensor válido exige soil_index calibrado')
        if not self.sensor_valid and self.soil_index is not None:
            raise ValueError('sensor inválido deve usar soil_index null')
        if self.source == 'simulation' and not self.experiment_id.startswith('sim-'):
            raise ValueError('experimento simulado exige prefixo sim-')
        if self.source == 'physical' and self.experiment_id.startswith('sim-'):
            raise ValueError('experimento físico não pode usar prefixo sim-')
        if self.source == 'simulation' and not self.device_id.startswith('sim-'):
            raise ValueError('dispositivo simulado exige prefixo sim-')
        if self.source == 'physical' and self.device_id.startswith('sim-'):
            raise ValueError('dispositivo simulado não pode produzir dado físico')
        return self
