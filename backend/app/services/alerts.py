from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.models.entities import Alert
from backend.app.schemas.requests import AlertConfig


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class AlertEngine:
    def __init__(self):
        self.config = AlertConfig()
        self.counters: dict[tuple[str, str], int] = defaultdict(int)
        self.clear_counters: dict[tuple[str, str], int] = defaultdict(int)

    def evaluate(self, db, machine, measurement, prediction) -> list[Alert]:
        cfg = self.config
        rules = []
        if prediction:
            rules.append(("anomaly", prediction["anomaly_score"], prediction["threshold"], "warning",
                          "Anomalie vibratoire persistante détectée par Isolation Forest"))
        if machine.mode == "simulation":
            rules.append(("vibration", measurement.rms, cfg.vibration_rms, "critical",
                          "Vibrations élevées — seuil de démonstration synthétique"))
            if measurement.temperature is not None:
                rules.append(("temperature", measurement.temperature, cfg.temperature, "critical",
                              "Échauffement anormal — seuil de démonstration synthétique"))
        changed = []
        for rule, value, threshold, severity, message in rules:
            key = (machine.id, rule)
            active = db.scalar(select(Alert).where(Alert.machine_id == machine.id, Alert.rule == rule,
                                                  Alert.resolved_at.is_(None)))
            self.counters[key] = self.counters[key] + 1 if value > threshold else 0
            self.clear_counters[key] = self.clear_counters[key] + 1 if value < threshold * cfg.hysteresis_ratio else 0
            if active:
                if self.clear_counters[key] >= cfg.clear_persistence:
                    active.resolved_at = utcnow()
                    changed.append(active)
                continue
            if self.counters[key] < cfg.persistence:
                continue
            latest = db.scalar(select(Alert).where(Alert.machine_id == machine.id, Alert.rule == rule)
                               .order_by(Alert.id.desc()))
            if latest and latest.resolved_at and (
                datetime.now(timezone.utc) - datetime.fromisoformat(latest.resolved_at)
            ).total_seconds() < cfg.cooldown_seconds:
                continue
            alert = Alert(machine_id=machine.id, measurement_id=measurement.id, rule=rule, severity=severity,
                          message=message, triggered_values={"value": value, "threshold": threshold,
                          "persistence": cfg.persistence, "industrial_validation": False}, created_at=utcnow())
            db.add(alert)
            changed.append(alert)
        return changed
