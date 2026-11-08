from typing import Literal
from pydantic import BaseModel, Field


class ReplayStart(BaseModel):
    trial: Literal["1st_test", "2nd_test", "3rd_test"]
    channel: int = Field(ge=1, le=8, default=1)
    speed: Literal[1, 10, 60] = 60
    start_index: int = Field(default=0, ge=0)


class SpeedUpdate(BaseModel):
    speed: Literal[1, 10, 60]


class SimulationStart(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    machine_count: int = Field(default=20, ge=1, le=20)


class ScenarioUpdate(BaseModel):
    scenario: Literal["normal", "degradation", "overheating", "imbalance", "bearing",
                      "vibration", "shutdown", "maintenance", "recovery"]


class MaintenanceCreate(BaseModel):
    machine_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(min_length=3, max_length=2000)
    priority: Literal["low", "normal", "high", "critical"] = "normal"
    status: Literal["open", "planned", "in_progress", "completed"] = "open"
    scheduled_at: str | None = Field(default=None, max_length=40)
    comments: str = Field(default="", max_length=4000)


class MaintenanceUpdate(BaseModel):
    status: Literal["open", "planned", "in_progress", "completed"]
    comments: str = Field(default="", max_length=4000)


class AlertConfig(BaseModel):
    persistence: int = Field(default=3, ge=1, le=100)
    clear_persistence: int = Field(default=3, ge=1, le=100)
    vibration_rms: float = Field(default=0.45, gt=0, le=100)
    temperature: float = Field(default=80, gt=25, le=200)
    hysteresis_ratio: float = Field(default=0.9, gt=0, lt=1)
    cooldown_seconds: int = Field(default=30, ge=0, le=86400)
    stale_seconds: int = Field(default=30, ge=10, le=3600)
