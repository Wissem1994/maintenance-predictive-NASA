from __future__ import annotations

from sqlalchemy import JSON, Boolean, CheckConstraint, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database.session import Base


class Machine(Base):
    __tablename__ = "machines"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    equipment_type: Mapped[str] = mapped_column(String(80))
    mode: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(24), default="stopped")
    commissioned_at: Mapped[str | None] = mapped_column(String(40))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    __table_args__ = (CheckConstraint("mode IN ('nasa', 'simulation')", name="ck_machine_mode"),)


class Sensor(Base):
    __tablename__ = "sensors"
    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    unit: Mapped[str] = mapped_column(String(60))
    sample_rate_hz: Mapped[float | None] = mapped_column(Float)


class Measurement(Base):
    __tablename__ = "measurements"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), index=True)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id"))
    measured_at: Mapped[str] = mapped_column(String(40))
    received_at: Mapped[str] = mapped_column(String(40))
    provenance: Mapped[str] = mapped_column(String(40))
    source_file: Mapped[str | None] = mapped_column(Text)
    source_sha256: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[str] = mapped_column(String(40), index=True)
    rms: Mapped[float] = mapped_column(Float)
    temperature: Mapped[float | None] = mapped_column(Float)
    speed_rpm: Mapped[float | None] = mapped_column(Float)
    torque_nm: Mapped[float | None] = mapped_column(Float)
    load_pct: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (Index("ix_measurement_machine_time", "machine_id", "measured_at"),
                     UniqueConstraint("machine_id", "session_id", "measured_at", name="uq_measurement_session"))


class SignalFeatures(Base):
    __tablename__ = "signal_features"
    measurement_id: Mapped[int] = mapped_column(ForeignKey("measurements.id"), primary_key=True)
    values_json: Mapped[dict] = mapped_column(JSON)
    window_start: Mapped[int] = mapped_column(Integer, default=0)
    window_size: Mapped[int] = mapped_column(Integer)
    sample_rate_hz: Mapped[float] = mapped_column(Float)


class ModelVersion(Base):
    __tablename__ = "model_versions"
    version: Mapped[str] = mapped_column(String(140), primary_key=True)
    metadata_json: Mapped[dict] = mapped_column(JSON)
    artifact_path: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    measurement_id: Mapped[int] = mapped_column(ForeignKey("measurements.id"), unique=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), index=True)
    model_version: Mapped[str] = mapped_column(ForeignKey("model_versions.version"))
    predicted_at: Mapped[str] = mapped_column(String(40))
    anomaly_score: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    baseline_z: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean)
    risk: Mapped[str] = mapped_column(String(30))
    health_index: Mapped[float | None] = mapped_column(Float)
    failure_probability: Mapped[float | None] = mapped_column(Float)


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), index=True)
    measurement_id: Mapped[int | None] = mapped_column(ForeignKey("measurements.id"))
    rule: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    triggered_values: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40), index=True)
    acknowledged_at: Mapped[str | None] = mapped_column(String(40))
    resolved_at: Mapped[str | None] = mapped_column(String(40))
    __table_args__ = (CheckConstraint("severity IN ('info', 'warning', 'critical')", name="ck_alert_severity"),)


class MaintenanceEvent(Base):
    __tablename__ = "maintenance_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.id"), index=True)
    reason: Mapped[str] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20))
    scheduled_at: Mapped[str | None] = mapped_column(String(40))
    comments: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))
    __table_args__ = (CheckConstraint("status IN ('open','planned','in_progress','completed')",
                                     name="ck_maintenance_status"),)


class ReplaySession(Base):
    __tablename__ = "replay_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    trial: Mapped[str] = mapped_column(String(20))
    channel: Mapped[int] = mapped_column(Integer)
    speed: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    cursor: Mapped[int] = mapped_column(Integer, default=0)
    total: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))


class SimulationSession(Base):
    __tablename__ = "simulation_sessions"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    seed: Mapped[int] = mapped_column(Integer)
    tick: Mapped[int] = mapped_column(Integer, default=0)
    machine_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))
