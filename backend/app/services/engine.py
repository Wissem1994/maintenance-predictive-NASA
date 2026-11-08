from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import datetime, timedelta
import logging
import time
import uuid

from sqlalchemy import select

from backend.app.models.entities import (
    Alert, Machine, Measurement, Prediction, ReplaySession, Sensor, SignalFeatures, SimulationSession,
)
from backend.app.services.alerts import AlertEngine, utcnow
from backend.app.services.registry import Registry
from backend.app.websocket.broker import Broker
from ml.features.signal import extract
from ml.ingestion.nasa import SAMPLE_RATE_HZ, bearing_for, discover, load_snapshot, sha256
from ml.training.anomaly import infer
from simulation.industrial import FS, TYPES, generate

logger = logging.getLogger(__name__)


class Engine:
    def __init__(self, settings, sessions):
        self.settings, self.sessions = settings, sessions
        self.broker, self.alerts = Broker(), AlertEngine()
        self.registry = Registry(settings.artifact_dir)
        self.task: asyncio.Task | None = None
        self.watchdog: asyncio.Task | None = None
        self.mode = "nasa"
        self.state: dict = {"status": "stopped", "mode": "nasa"}
        self.snapshots = []
        self.next_due = 0.0
        self.scenarios: dict[str, tuple[str, int]] = {}
        self.lock = asyncio.Lock()

    def initialize(self):
        with self.sessions() as db:
            # Sessions interrupted by process shutdown remain auditable but never run unnoticed.
            for cls in (ReplaySession, SimulationSession):
                for session in db.scalars(select(cls).where(cls.status.in_(["running", "paused"]))):
                    session.status = "interrupted"
                    session.updated_at = utcnow()
            for machine in db.scalars(select(Machine)):
                machine.status = "stopped"
            db.commit()
            self.registry.sync(db)

    async def close(self):
        for task in (self.task, self.watchdog):
            if task:
                task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    def _record(self, db, machine, signal, measured_at, session_id, extra=None, source=None, simulation=None):
        extra = extra or {}
        features = extract(signal, SAMPLE_RATE_HZ)
        now = utcnow()
        for missing in db.scalars(select(Alert).where(Alert.machine_id == machine.id,
                                  Alert.rule == "missing", Alert.resolved_at.is_(None))):
            missing.resolved_at = now
        measurement = Measurement(machine_id=machine.id, sensor_id=machine.id + "-vibration",
                                  measured_at=measured_at, received_at=now, provenance=(
                                      "experimental_historical" if machine.mode == "nasa" else "synthetic"),
                                  session_id=session_id, source_file=str(source) if source else None,
                                  source_sha256=sha256(source) if source else None, rms=features["rms"],
                                  temperature=extra.get("temperature"), speed_rpm=extra.get("speed_rpm"),
                                  torque_nm=extra.get("torque_nm"), load_pct=extra.get("load_pct"))
        db.add(measurement)
        db.flush()
        values = {**features, **({"_simulation": simulation} if simulation else {})}
        db.add(SignalFeatures(measurement_id=measurement.id, values_json=values, window_start=0,
                              window_size=len(signal), sample_rate_hz=SAMPLE_RATE_HZ))
        bundle = self.registry.for_machine(db, machine)
        prediction = infer(bundle, features) if bundle else None
        if prediction:
            db.add(Prediction(measurement_id=measurement.id, machine_id=machine.id, predicted_at=now,
                              **prediction))
        changed = self.alerts.evaluate(db, machine, measurement, prediction)
        machine.status = "stopped" if extra.get("operating_state") == "stopped" else (
            "anomaly" if prediction and prediction["is_anomaly"] else "running")
        return changed

    async def replay_start(self, config):
        async with self.lock:
            if self.state["status"] in {"running", "paused"}:
                raise ValueError("Arrêter la session active avant d'en démarrer une autre")
            bearing = bearing_for(config.trial, config.channel)
            snapshots = await asyncio.to_thread(discover, self.settings.raw_dir, config.trial)
            if not snapshots:
                raise ValueError("Essai NASA absent. Importer les fichiers réels dans data/raw/nasa_ims.")
            if config.start_index >= len(snapshots):
                raise ValueError("Index de départ hors de l'essai")
            self.snapshots = snapshots
            session_id = str(uuid.uuid4())
            now = utcnow()
            with self.sessions() as db:
                machine_id = f"nasa-{config.trial}-ch{config.channel}"
                if db.get(Machine, machine_id) is None:
                    db.add(Machine(id=machine_id, name=f"IMS · {config.trial} · Roulement {bearing} / Ch {config.channel}",
                                   equipment_type="Roulement expérimental", mode="nasa", status="running",
                                   metadata_json={"trial": config.trial, "channel": config.channel, "bearing": bearing,
                                                  "unit": "amplitude source — calibration non vérifiée",
                                                  "sample_rate_hz": SAMPLE_RATE_HZ,
                                                  "timezone": "horloge locale expérimentale, fuseau inconnu"}))
                    db.flush()
                    db.add(Sensor(id=machine_id + "-vibration", machine_id=machine_id, kind="vibration",
                                  unit="amplitude_source", sample_rate_hz=SAMPLE_RATE_HZ))
                db.add(ReplaySession(id=session_id, trial=config.trial, channel=config.channel,
                                     speed=config.speed, status="running", cursor=config.start_index,
                                     total=len(snapshots), created_at=now, updated_at=now))
                db.commit()
            self.mode = "nasa"
            self.state = {"mode": "nasa", "status": "running", "session_id": session_id,
                          "trial": config.trial, "channel": config.channel, "speed": config.speed,
                          "cursor": config.start_index, "total": len(snapshots), "machine_id": machine_id,
                          "measured_at": None, "received_at": None}
            self.next_due = time.monotonic()
            await self.broker.publish({"type": "state", "state": self.state.copy()})

    async def simulation_start(self, config):
        async with self.lock:
            if self.state["status"] in {"running", "paused"}:
                raise ValueError("Arrêter la session active avant de changer de mode")
            now, session_id = utcnow(), str(uuid.uuid4())
            with self.sessions() as db:
                for i in range(config.machine_count):
                    mid = f"sim-{i + 1:02}"
                    machine = db.get(Machine, mid)
                    if machine is None:
                        machine = Machine(id=mid, name=f"{TYPES[i % 5]} {i + 1:02}", mode="simulation",
                                          equipment_type=TYPES[i % 5], status="running", commissioned_at="2022-01-01",
                                          metadata_json={"index": i, "commissioned_fictitious": True,
                                                         "unit": "g synthétique", "nominal_rpm": 1500 if i % 2 else 2000})
                        db.add(machine)
                        db.flush()
                        db.add(Sensor(id=mid + "-vibration", machine_id=mid, kind="vibration", unit="g_synthetic",
                                      sample_rate_hz=FS))
                    machine.status = "running"
                db.add(SimulationSession(id=session_id, seed=config.seed, tick=0,
                                         machine_count=config.machine_count, status="running",
                                         created_at=now, updated_at=now))
                db.commit()
            self.scenarios.clear()
            self.mode = "simulation"
            self.state = {"mode": "simulation", "status": "running", "session_id": session_id,
                          "seed": config.seed, "machine_count": config.machine_count, "tick": 0,
                          "created_at": now}
            self.next_due = time.monotonic()
            await self.broker.publish({"type": "state", "state": self.state.copy()})

    async def control(self, action: str, speed=None):
        async with self.lock:
            if action == "speed":
                if self.mode != "nasa" or self.state["status"] not in {"running", "paused"}:
                    raise ValueError("Aucun rejeu NASA actif")
                remaining = self.state.get("remaining_seconds", max(0.0, self.next_due - time.monotonic()))
                remaining = remaining * self.state["speed"] / speed
                self.state["speed"] = speed
                if self.state["status"] == "paused":
                    self.state["remaining_seconds"] = remaining
                self.next_due = time.monotonic() + remaining
            elif action == "resume":
                if self.state["status"] != "paused":
                    raise ValueError("Aucune session en pause")
                self.state["status"] = "running"
                self.next_due = time.monotonic() + self.state.pop("remaining_seconds", 0)
            elif action == "pause":
                if self.state["status"] != "running":
                    raise ValueError("Aucune session en cours")
                self.state["remaining_seconds"] = max(0, self.next_due - time.monotonic())
                self.state["status"] = "paused"
            elif action in {"stop", "reset"}:
                self.state["status"] = "stopped"
                if action == "reset" and self.mode == "nasa":
                    self.state["cursor"] = 0
            with self.sessions() as db:
                cls = ReplaySession if self.mode == "nasa" else SimulationSession
                session = db.get(cls, self.state.get("session_id", ""))
                if session:
                    session.status, session.updated_at = self.state["status"], utcnow()
                    if self.mode == "nasa":
                        session.cursor, session.speed = self.state["cursor"], self.state["speed"]
                if action in {"stop", "reset"}:
                    for machine in db.scalars(select(Machine).where(Machine.mode == self.mode)):
                        machine.status = "stopped"
                db.commit()
            await self.broker.publish({"type": "state", "state": self.state.copy()})

    def _historical_gap(self):
        cursor = self.state.get("cursor", 0)
        if cursor <= 0 or cursor >= len(self.snapshots):
            return 0.0
        return max(0.0, (self.snapshots[cursor].measured_at - self.snapshots[cursor - 1].measured_at).total_seconds())

    def _replay_tick(self):
        item = self.snapshots[self.state["cursor"]]
        signal = load_snapshot(item)[:, self.state["channel"] - 1]
        with self.sessions() as db:
            machine = db.get(Machine, self.state["machine_id"])
            changes = self._record(db, machine, signal, item.measured_at.isoformat(), self.state["session_id"],
                                   source=item.path.resolve())
            session = db.get(ReplaySession, self.state["session_id"])
            session.cursor += 1
            session.updated_at = utcnow()
            self.state["cursor"] = session.cursor
            self.state["measured_at"], self.state["received_at"] = item.measured_at.isoformat(), utcnow()
            if session.cursor >= session.total:
                self.state["status"] = session.status = "completed"
                machine.status = "stopped"
            db.commit()
            return len(changes)

    def _simulation_tick(self):
        tick, seed = self.state["tick"], self.state["seed"]
        count = 0
        measured_at = (datetime.fromisoformat(self.state["created_at"]) +
                       timedelta(seconds=tick * self.settings.tick_seconds)).isoformat()
        with self.sessions() as db:
            for i in range(self.state["machine_count"]):
                machine = db.get(Machine, f"sim-{i + 1:02}")
                scenario, since = self.scenarios.get(machine.id, ("normal", 0))
                config = {"seed": seed, "machine_index": i, "tick": tick, "scenario": scenario,
                          "age": tick - since}
                data = generate(**config)
                count += len(self._record(db, machine, data["signal"], measured_at, self.state["session_id"],
                                         extra=data, simulation=config))
            session = db.get(SimulationSession, self.state["session_id"])
            session.tick, session.updated_at = tick + 1, utcnow()
            self.state["tick"] = tick + 1
            self.state["received_at"] = utcnow()
            db.commit()
        return count

    def _check_stale(self):
        # Respect the next expected acquisition: NASA gaps are not missing live packets.
        if self.state["status"] != "running" or time.monotonic() <= self.next_due + self.alerts.config.stale_seconds:
            return 0
        ids = [self.state["machine_id"]] if self.mode == "nasa" else [
            f"sim-{i + 1:02}" for i in range(self.state["machine_count"])]
        changed = 0
        with self.sessions() as db:
            for mid in ids:
                active = db.scalar(select(Alert).where(Alert.machine_id == mid, Alert.rule == "missing",
                                                      Alert.resolved_at.is_(None)))
                if active is None:
                    db.add(Alert(machine_id=mid, rule="missing", severity="warning",
                                 message="Absence de mesure au-delà de l’échéance attendue",
                                 triggered_values={"grace_seconds": self.alerts.config.stale_seconds},
                                 created_at=utcnow()))
                    changed += 1
            db.commit()
        return changed

    async def monitor(self):
        while True:
            await asyncio.sleep(5)
            try:
                changed = await asyncio.to_thread(self._check_stale)
                if changed:
                    await self.broker.publish({"type": "alert", "alerts_changed": changed})
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Surveillance des absences indisponible")

    async def run(self):
        while True:
            try:
                async with self.lock:
                    if self.state["status"] == "running" and time.monotonic() >= self.next_due:
                        changes = await asyncio.to_thread(self._replay_tick if self.mode == "nasa"
                                                          else self._simulation_tick)
                        self.next_due = time.monotonic() + (self._historical_gap() / self.state["speed"]
                                                          if self.mode == "nasa" else self.settings.tick_seconds)
                        await self.broker.publish({"type": "update", "mode": self.mode,
                                                   "alerts_changed": changes, "state": self.state.copy()})
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.exception("Échec du moteur d'acquisition")
                self.state["status"], self.state["error"] = "error", str(exc)
                await self.broker.publish({"type": "error", "message": str(exc), "state": self.state.copy()})
            await asyncio.sleep(0.1)
