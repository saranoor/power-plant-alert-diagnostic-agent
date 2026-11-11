from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CauseLabel = Literal[
    "offline_units",
    "hot_modules",
    "low_irradiance",
    "string_underperformance",
    "grid_curtailment",
    "unknown",
]


class Alarm(BaseModel):
    code: str
    text: str
    severity: str


class PlantState(BaseModel):
    mode: str
    curtailed: bool


class Weather(BaseModel):
    poa_w_m2: float
    module_temp_c: float
    ambient_c: float


class Readings(BaseModel):
    ac_power_kw: float
    expected_ac_power_kw: float | None = None
    dc_voltage_v: float
    strings_below_expected: list[str] | None = None


class Alert(BaseModel):
    alert_id: str
    timestamp_utc: str
    plant: str
    asset: str
    alarm: Alarm
    state: PlantState
    weather: Weather | None = None
    readings: Readings
    data_quality: str | None = None
    related_alarms_last_30min: list[str] | None = None
    recent_events: list[str] | None = None


class ToolResult(BaseModel):
    call_id: str
    evidence_id: str
    tool_name: str
    arguments: dict[str, object]
    result: object
    is_error: bool


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: str
    predicted_cause: CauseLabel
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    recommended_action: str
    tool_results: list[ToolResult] = Field(default_factory=list)
