from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
import logging
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.inspection import inspect
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import Settings
from backend.app.database.session import make_database
from backend.app.models.entities import (
    Alert, Machine, MaintenanceEvent, Measurement, ModelVersion, Prediction, Sensor, SignalFeatures,
)
from backend.app.schemas.requests import (
    AlertConfig, MaintenanceCreate, MaintenanceUpdate, ReplayStart, ScenarioUpdate, SimulationStart, SpeedUpdate,
)
from backend.app.services.alerts import utcnow
from backend.app.services.engine import Engine
from ml.features.signal import preview
from ml.ingestion.nasa import CHANNELS, SAMPLE_RATE_HZ, bearing_for, discover, load_snapshot, Snapshot
from simulation.industrial import generate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def serialize(record):
    if record is None:
        return None
    return {column.key: getattr(record, column.key) for column in inspect(record).mapper.column_attrs}


def page(db, stmt, limit, offset):
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    return {"items": [serialize(row) for row in db.scalars(stmt.limit(limit).offset(offset))],
            "total": total, "limit": limit, "offset": offset}


def create_app(settings: Settings | None = None, background: bool = True) -> FastAPI:
    settings = settings or Settings()
    Path("data").mkdir(exist_ok=True)
    db_engine, sessions = make_database(settings.database_url)
    engine = Engine(settings, sessions)

    @asynccontextmanager
    async def lifespan(app):
        if not inspect(db_engine).has_table("machines"):
            raise RuntimeError("Base non initialisée : exécuter python -m scripts.init_db")
        engine.initialize()
        # Register real experimental channels without inventing any observations.
        items = await asyncio.to_thread(discover, settings.raw_dir)
        with sessions() as db:
            for trial in sorted({s.trial for s in items}):
                for channel in range(1, CHANNELS[trial] + 1):
                    mid = f"nasa-{trial}-ch{channel}"
                    if db.get(Machine, mid):
                        continue
                    bearing = bearing_for(trial, channel)
                    db.add(Machine(id=mid, name=f"IMS · {trial} · Roulement {bearing} / Ch {channel}",
                                   equipment_type="Roulement expérimental", mode="nasa", status="stopped",
                                   metadata_json={"trial": trial, "channel": channel, "bearing": bearing,
                                                  "unit": "amplitude source — calibration non vérifiée",
                                                  "sample_rate_hz": SAMPLE_RATE_HZ,
                                                  "timezone": "horloge expérimentale, fuseau inconnu"}))
                    db.flush()
                    db.add(Sensor(id=mid + "-vibration", machine_id=mid, kind="vibration",
                                  unit="amplitude_source", sample_rate_hz=SAMPLE_RATE_HZ))
            db.commit()
        if background:
            engine.task = asyncio.create_task(engine.run())
            engine.watchdog = asyncio.create_task(engine.monitor())
        yield
        await engine.close()
        db_engine.dispose()

    app = FastAPI(title="PredictMaint AI", version="0.1.0", lifespan=lifespan,
                  description="Supervision locale · NASA IMS expérimental et simulation séparés. "
                              "Aucune probabilité de panne validée n'est disponible.")
    app.add_middleware(CORSMiddleware, allow_origins=settings.origins.split(","),
                       allow_methods=["GET", "POST", "PATCH", "PUT"], allow_headers=["Content-Type"])
    app.state.engine, app.state.sessions = engine, sessions

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        from fastapi.responses import JSONResponse
        logger.error("Erreur de persistance : %s", type(exc).__name__)
        return JSONResponse(status_code=503, content={"detail": "Base de données indisponible. Consulter les journaux."})

    def required(db, cls, identity):
        record = db.get(cls, identity)
        if record is None:
            raise HTTPException(404, "Ressource introuvable")
        return record

    @app.get("/api/health", tags=["Système"])
    def health():
        with sessions() as db:
            db.execute(select(1))
        return {"status": "ok", "version": "0.1.0", "database": "connected", "engine": engine.state.copy()}

    @app.get("/api/datasets", tags=["Données"])
    def datasets():
        items = discover(settings.raw_dir)
        trials = []
        for trial in sorted({s.trial for s in items}):
            subset = [s for s in items if s.trial == trial]
            trials.append({"trial": trial, "files": len(subset), "channels": CHANNELS[trial],
                           "first": subset[0].measured_at.isoformat(), "last": subset[-1].measured_at.isoformat()})
        return {"nasa_ims": {"available": bool(items), "trials": trials, "sample_rate_hz": SAMPLE_RATE_HZ,
                            "provenance": "experimental_historical", "timezone": "unknown_experiment_local",
                            "source": "https://data.nasa.gov/dataset/ims-bearings",
                            "import_command": "python -m scripts.import_nasa --trial 2nd_test"},
                "paderborn": {"available": False, "status": "non importé", "license": "CC BY-NC 4.0"},
                "ai4i": {"available": (settings.raw_dir.parent / "ai4i/ai4i2020.csv").exists(), "status": "voir le registre des modèles", "provenance": "synthetic"}}

    @app.get("/api/summary", tags=["Supervision"])
    def summary(mode: Literal["nasa", "simulation"] = "nasa"):
        with sessions() as db:
            def machine_count(*conditions):
                return db.scalar(select(func.count(Machine.id)).where(Machine.mode == mode, *conditions))
            def alert_count(*conditions):
                return db.scalar(select(func.count(Alert.id)).join(Machine).where(Machine.mode == mode, *conditions))
            return {"machines": machine_count(), "running": machine_count(Machine.status.in_(["running", "anomaly"])),
                    "stopped": machine_count(Machine.status == "stopped"),
                    "anomalies": machine_count(Machine.status == "anomaly"),
                    "unacknowledged": alert_count(Alert.acknowledged_at.is_(None), Alert.resolved_at.is_(None)),
                    "critical_active": alert_count(Alert.severity == "critical", Alert.resolved_at.is_(None))}

    @app.get("/api/engine", tags=["Acquisition"])
    def engine_state():
        return engine.state.copy()

    @app.get("/api/machines", tags=["Machines"])
    def machines(mode: Literal["nasa", "simulation"] = "nasa", limit: int = Query(50, ge=1, le=100),
                 offset: int = Query(0, ge=0)):
        with sessions() as db:
            result = page(db, select(Machine).where(Machine.mode == mode).order_by(Machine.id), limit, offset)
            for item in result["items"]:
                latest = db.scalar(select(Measurement).where(Measurement.machine_id == item["id"])
                                   .order_by(Measurement.id.desc()).limit(1))
                item["latest"] = serialize(latest)
                item["prediction"] = serialize(db.scalar(select(Prediction)
                    .where(Prediction.measurement_id == latest.id))) if latest else None
            return result

    @app.get("/api/machines/{machine_id}", tags=["Machines"])
    def machine_detail(machine_id: str):
        with sessions() as db:
            machine = required(db, Machine, machine_id)
            result = serialize(machine)
            result["sensors"] = [serialize(s) for s in db.scalars(select(Sensor).where(Sensor.machine_id == machine_id))]
            return result

    @app.get("/api/machines/{machine_id}/measurements", tags=["Machines"])
    def measurements(machine_id: str, limit: int = Query(200, ge=1, le=2000),
                     offset: int = Query(0, ge=0), since: str | None = None, until: str | None = None,
                     session_id: str | None = None):
        with sessions() as db:
            required(db, Machine, machine_id)
            stmt = select(Measurement).where(Measurement.machine_id == machine_id)
            if since:
                stmt = stmt.where(Measurement.measured_at >= since)
            if until:
                stmt = stmt.where(Measurement.measured_at <= until)
            if session_id:
                stmt = stmt.where(Measurement.session_id == session_id)
            result = page(db, stmt.order_by(Measurement.id.desc()), limit, offset)
            for row in result["items"]:
                feature = db.get(SignalFeatures, row["id"])
                row["features"] = feature.values_json if feature else {}
                row["prediction"] = serialize(db.scalar(select(Prediction).where(Prediction.measurement_id == row["id"])))
            return result

    @app.get("/api/machines/{machine_id}/predictions", tags=["Machines"])
    def predictions(machine_id: str, limit: int = Query(200, ge=1, le=2000), offset: int = Query(0, ge=0)):
        with sessions() as db:
            required(db, Machine, machine_id)
            return page(db, select(Prediction).where(Prediction.machine_id == machine_id)
                        .order_by(Prediction.id.desc()), limit, offset)

    @app.get("/api/machines/{machine_id}/signal", tags=["Signaux"])
    def signal_preview(machine_id: str, measurement_id: int | None = None):
        with sessions() as db:
            machine = required(db, Machine, machine_id)
            measurement = db.get(Measurement, measurement_id) if measurement_id else db.scalar(
                select(Measurement).where(Measurement.machine_id == machine_id).order_by(Measurement.id.desc()))
            if measurement is None or measurement.machine_id != machine_id:
                raise HTTPException(404, "Aucune mesure disponible pour cette machine")
            feature = db.get(SignalFeatures, measurement.id)
            if machine.mode == "nasa":
                source = Path(measurement.source_file).resolve()
                if not source.is_relative_to(settings.raw_dir.resolve()) or not source.is_file():
                    raise HTTPException(404, "Fichier source absent du répertoire de données")
                item = Snapshot(source, machine.metadata_json["trial"],
                                datetime.fromisoformat(measurement.measured_at))
                values = load_snapshot(item)[:, machine.metadata_json["channel"] - 1]
            else:
                values = generate(**feature.values_json["_simulation"])["signal"]
            return {**preview(values, feature.sample_rate_hz), "provenance": measurement.provenance,
                    "measured_at": measurement.measured_at, "measurement_id": measurement.id}

    @app.get("/api/alerts", tags=["Alertes"])
    def alerts(mode: Literal["nasa", "simulation"] = "nasa", status: Literal["open", "acknowledged", "resolved"] | None = None,
               severity: Literal["info", "warning", "critical"] | None = None,
               machine_id: str | None = None, search: str | None = Query(None, max_length=100),
               limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        stmt = select(Alert).join(Machine).where(Machine.mode == mode)
        if status == "open":
            stmt = stmt.where(Alert.resolved_at.is_(None), Alert.acknowledged_at.is_(None))
        elif status == "acknowledged":
            stmt = stmt.where(Alert.acknowledged_at.is_not(None), Alert.resolved_at.is_(None))
        elif status == "resolved":
            stmt = stmt.where(Alert.resolved_at.is_not(None))
        if severity:
            stmt = stmt.where(Alert.severity == severity)
        if machine_id:
            stmt = stmt.where(Alert.machine_id == machine_id)
        if search:
            stmt = stmt.where(Alert.message.contains(search, autoescape=True))
        with sessions() as db:
            return page(db, stmt.order_by(Alert.id.desc()), limit, offset)

    @app.post("/api/alerts/{alert_id}/acknowledge", tags=["Alertes"])
    async def acknowledge(alert_id: int):
        with sessions() as db:
            record = required(db, Alert, alert_id)
            if record.resolved_at:
                raise HTTPException(409, "Cette alerte est déjà résolue")
            record.acknowledged_at = record.acknowledged_at or utcnow()
            db.commit()
            result = serialize(record)
        await engine.broker.publish({"type": "alert", "alert": result})
        return result

    @app.post("/api/alerts/{alert_id}/resolve", tags=["Alertes"])
    async def resolve(alert_id: int):
        with sessions() as db:
            record = required(db, Alert, alert_id)
            record.resolved_at = record.resolved_at or utcnow()
            db.commit()
            result = serialize(record)
        await engine.broker.publish({"type": "alert", "alert": result})
        return result

    @app.get("/api/alert-config", tags=["Alertes"])
    def alert_config():
        return {**engine.alerts.config.model_dump(), "industrial_validation": False, "config_scope": "runtime_only"}

    @app.put("/api/alert-config", tags=["Alertes"])
    def configure_alerts(config: AlertConfig):
        engine.alerts.config = config
        return config.model_dump()

    @app.get("/api/maintenance", tags=["Maintenance"])
    def maintenance(mode: Literal["nasa", "simulation"] = "nasa", machine_id: str | None = None,
                    limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
        stmt = select(MaintenanceEvent).join(Machine).where(Machine.mode == mode)
        if machine_id:
            stmt = stmt.where(MaintenanceEvent.machine_id == machine_id)
        with sessions() as db:
            return page(db, stmt.order_by(MaintenanceEvent.id.desc()), limit, offset)

    @app.post("/api/maintenance", status_code=201, tags=["Maintenance"])
    def create_maintenance(config: MaintenanceCreate):
        with sessions() as db:
            required(db, Machine, config.machine_id)
            if config.scheduled_at:
                try:
                    datetime.fromisoformat(config.scheduled_at)
                except ValueError:
                    raise HTTPException(422, "scheduled_at doit être une date ISO 8601")
            record = MaintenanceEvent(**config.model_dump(), created_at=utcnow(), updated_at=utcnow())
            db.add(record)
            db.commit()
            return serialize(record)

    @app.patch("/api/maintenance/{event_id}", tags=["Maintenance"])
    def update_maintenance(event_id: int, config: MaintenanceUpdate):
        with sessions() as db:
            record = required(db, MaintenanceEvent, event_id)
            record.status, record.comments, record.updated_at = config.status, config.comments, utcnow()
            db.commit()
            return serialize(record)

    @app.get("/api/models", tags=["Modèles"])
    def models():
        with sessions() as db:
            return {"items": [serialize(row) for row in db.scalars(select(ModelVersion)
                    .order_by(ModelVersion.version))], "failure_probability_available": False}

    @app.post("/api/models/reload", tags=["Modèles"])
    async def reload_models():
        async with engine.lock:
            with sessions() as db:
                engine.registry.sync(db)
            engine.registry.bundles.clear()
        return {"status": "reloaded"}

    @app.post("/api/replay/start", tags=["Acquisition"])
    async def replay_start(config: ReplayStart):
        try:
            await engine.replay_start(config)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        return engine.state.copy()

    @app.post("/api/simulation/start", tags=["Acquisition"])
    async def simulation_start(config: SimulationStart):
        try:
            await engine.simulation_start(config)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        return engine.state.copy()

    @app.post("/api/simulation/{machine_id}/scenario", tags=["Acquisition"])
    async def scenario(machine_id: str, config: ScenarioUpdate):
        async with engine.lock:
            if engine.mode != "simulation" or engine.state["status"] not in {"running", "paused"}:
                raise HTTPException(409, "Démarrer la simulation")
            with sessions() as db:
                machine = required(db, Machine, machine_id)
                if machine.mode != "simulation" or machine.metadata_json["index"] >= engine.state["machine_count"]:
                    raise HTTPException(409, "Machine hors de la simulation active")
            engine.scenarios[machine_id] = (config.scenario, engine.state["tick"])
            if config.scenario in {"shutdown", "maintenance", "recovery"}:
                with sessions() as db:
                    db.add(Alert(machine_id=machine_id, rule="scenario", severity="info",
                                 message=f"Scenario synthetique commande : {config.scenario}",
                                 triggered_values={"scenario": config.scenario}, created_at=utcnow()))
                    db.commit()
        return {"machine_id": machine_id, "scenario": config.scenario, "since_tick": engine.state["tick"]}

    async def control(action, speed=None):
        try:
            await engine.control(action, speed)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        return engine.state.copy()

    @app.post("/api/replay/pause", tags=["Acquisition"])
    async def pause():
        return await control("pause")

    @app.post("/api/replay/resume", tags=["Acquisition"])
    async def resume():
        return await control("resume")

    @app.post("/api/replay/stop", tags=["Acquisition"])
    async def stop():
        return await control("stop")

    @app.post("/api/replay/reset", tags=["Acquisition"])
    async def reset():
        return await control("reset")

    @app.post("/api/replay/speed", tags=["Acquisition"])
    async def speed(config: SpeedUpdate):
        return await control("speed", config.speed)

    @app.websocket("/ws")
    async def websocket(websocket: WebSocket):
        origin = websocket.headers.get("origin")
        if origin and origin not in settings.origins.split(","):
            await websocket.close(code=1008)
            return
        await websocket.accept()
        queue = engine.broker.subscribe()
        try:
            await websocket.send_json({"type": "state", "state": engine.state.copy()})
            while True:
                try:
                    message = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    message = {"type": "heartbeat", "time": utcnow()}
                await websocket.send_json(message)
        except (WebSocketDisconnect, RuntimeError, OSError):
            pass
        finally:
            engine.broker.unsubscribe(queue)

    return app


app = create_app()
