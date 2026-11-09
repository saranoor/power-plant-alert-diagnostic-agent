from pydantic import BaseModel, ConfigDict, Field


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
    # expected_ac_power_kw: float
    dc_voltage_v: float
    # strings_below_expected: list[str]


class Alert(BaseModel):
    alert_id: str
    timestamp_utc: str
    plant: str
    asset: str
    alarm: Alarm
    state: PlantState
    # weather: Weather
    readings: Readings
    # data_quality: str
    # related_alarms_last_30min: list[str]
    # recent_events: list[str]


class ToolResult(BaseModel):
    call_id: str
    tool_name: str
    arguments: dict[str, object]
    result: object
    is_error: bool


class Diagnosis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    diagnosis: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str]
    recommended_action: str
    tool_results: list[ToolResult] = Field(default_factory=list)
