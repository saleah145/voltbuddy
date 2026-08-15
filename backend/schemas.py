from typing import Optional
from pydantic import BaseModel, Field, field_validator


class SimulationRequest(BaseModel):
    hour: int = Field(ge=0, le=23)
    appliances: list[str] = Field(min_length=1)
    month: int = Field(default=8, ge=1, le=12)
    weekday: int = Field(default=2, ge=0, le=6)

    @field_validator("appliances")
    @classmethod
    def validate_appliances(cls, value):
        cleaned = [x.strip() for x in value if isinstance(x, str) and x.strip()]
        if not cleaned:
            raise ValueError("Select at least one appliance.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate appliance selections are not allowed.")
        return cleaned


class ApplianceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kw: float = Field(gt=0, le=50)
    interruptible: bool
    priority: str
    category: Optional[str] = Field(default=None, max_length=80)
    brand: Optional[str] = Field(default=None, max_length=80)
    model_number: Optional[str] = Field(default=None, max_length=120)
    annual_kwh: Optional[float] = Field(default=None, gt=0)
    typical_runtime_hours: Optional[float] = Field(default=None, gt=0, le=24)
    preferred_start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    earliest_start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    latest_finish_hour: Optional[int] = Field(default=None, ge=0, le=23)
    schedule_flexibility: Optional[str] = Field(default="auto", max_length=20)
    source: Optional[str] = Field(default=None, max_length=200)
    is_estimate: bool = False

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Appliance name is required.")
        return cleaned

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value):
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "critical"}:
            raise ValueError("Priority must be low, medium, or critical.")
        return normalized


    @field_validator("schedule_flexibility")
    @classmethod
    def validate_schedule_flexibility(cls, value):
        normalized = (value or "auto").strip().lower()
        if normalized not in {"auto", "fixed", "window", "anytime"}:
            raise ValueError("Schedule flexibility must be auto, fixed, window, or anytime.")
        return normalized


class ApplianceUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kw: float = Field(gt=0, le=50)
    interruptible: bool
    priority: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, value):
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Appliance name is required.")
        return cleaned

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value):
        normalized = value.strip().lower()
        if normalized not in {"low", "medium", "critical"}:
            raise ValueError("Priority must be low, medium, or critical.")
        return normalized


class HomeCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    appliances: list[str] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def validate_home_name(cls, value):
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("Home name is required.")
        return cleaned

    @field_validator("appliances")
    @classmethod
    def validate_home_appliances(cls, value):
        cleaned = [x.strip() for x in value if isinstance(x, str) and x.strip()]
        if not cleaned:
            raise ValueError("Select at least one appliance.")
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate appliance selections are not allowed.")
        return cleaned
