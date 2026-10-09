from pydantic import BaseModel


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
    expected_ac_power_kw: float
    dc_voltage_v: float
    strings_below_expected: list[str]


class Alert(BaseModel):
    alert_id: str
    timestamp_utc: str
    plant: str
    asset: str
    alarm: Alarm
    state: PlantState
    weather: Weather
    readings: Readings
    data_quality: str
    related_alarms_last_30min: list[str]
    recent_events: list[str]


class Diagnosis(BaseModel):
    diagnosis: str
    confidence: float
    evidence: list[str]
    recommended_action: str
