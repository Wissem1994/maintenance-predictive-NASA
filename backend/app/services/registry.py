import json
from pathlib import Path

import joblib
from sqlalchemy import select

from backend.app.models.entities import ModelVersion


class Registry:
    def __init__(self, path: Path):
        self.path = path
        self.bundles: dict[str, dict] = {}

    def sync(self, db):
        self.path.mkdir(parents=True, exist_ok=True)
        for path in self.path.glob("*.json"):
            meta = json.loads(path.read_text(encoding="utf-8"))
            artifact = path.with_suffix(".joblib")
            if not artifact.exists() or "provenance" not in meta:
                continue
            record = db.get(ModelVersion, meta["version"])
            if record is None:
                db.add(ModelVersion(version=meta["version"], metadata_json=meta,
                                    artifact_path=str(artifact.resolve()), active=True))
        db.flush()
        newest: dict[tuple, ModelVersion] = {}
        for record in db.scalars(select(ModelVersion).order_by(ModelVersion.version)):
            p = record.metadata_json["provenance"]
            key = (p["dataset"], p.get("trial"), p.get("channel"))
            if key not in newest or record.metadata_json["trained_at"] > newest[key].metadata_json["trained_at"]:
                newest[key] = record
            record.active = False
        for record in newest.values():
            record.active = True
        db.commit()

    def for_machine(self, db, machine) -> dict | None:
        meta = machine.metadata_json
        for record in db.scalars(select(ModelVersion).where(ModelVersion.active.is_(True))):
            p = record.metadata_json["provenance"]
            matches = p["dataset"] == "industrial_simulation" if machine.mode == "simulation" else (
                p["dataset"] == "nasa_ims" and p.get("trial") == meta.get("trial")
                and p.get("channel") == meta.get("channel"))
            if matches:
                if record.version not in self.bundles:
                    # Artifacts are administrator-created local files. Never deserialize user uploads.
                    self.bundles[record.version] = joblib.load(record.artifact_path)
                return self.bundles[record.version]
        return None
