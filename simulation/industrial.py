"""Educational synthetic generator. Not a digital twin or ISO vibration severity model."""
from __future__ import annotations

import numpy as np
from ml.features.signal import extract

SCENARIOS = ("normal", "degradation", "overheating", "imbalance", "bearing", "vibration",
             "shutdown", "maintenance", "recovery")
TYPES = ("Réducteur industriel", "Multiplicateur de vitesse", "Moteur électrique",
         "Roulement", "Machine tournante")
FS = 20_000
SAMPLES = 4096


def generate(seed: int, machine_index: int, tick: int, scenario: str = "normal", age: int = 0) -> dict:
    if scenario not in SCENARIOS or min(tick, age, machine_index, seed) < 0:
        raise ValueError("Configuration du simulateur invalide")
    rng = np.random.default_rng(np.random.SeedSequence([seed, machine_index, tick]))
    nominal_rpm = 1500 if machine_index % 2 else 2000
    load = float(65 + 12 * np.sin(tick / 35 + machine_index))
    severity = min(1.0, age / 20) if scenario in {"degradation", "bearing", "vibration"} else 0.0
    if scenario in {"shutdown", "maintenance"}:
        rpm, temp, amplitude = 0.0, 25 + 30 * np.exp(-age / 10), 0.001
    else:
        rpm = nominal_rpm * (1 + 0.003 * np.sin(tick / 10))
        amplitude = 0.105 * (1 + load / 200) + 0.8 * severity
        if scenario == "imbalance":
            amplitude += 0.5 * (1 - np.exp(-age / 4))
        temp = 25 + (load * 0.5 + severity * 40) * (1 - np.exp(-(tick + 10) / 15))
        if scenario == "overheating":
            temp += 65 * (1 - np.exp(-age / 8))
        if scenario == "recovery":
            amplitude += 0.5 * np.exp(-age / 5)
            temp += 35 * np.exp(-age / 8)
    t = np.arange(SAMPLES) / FS
    x = amplitude * np.sin(2 * np.pi * max(rpm / 60, 1) * t)
    x += 0.03 * np.sin(2 * np.pi * 1200 * t) + rng.normal(0, 0.025, SAMPLES)
    if scenario in {"bearing", "degradation"} and severity > 0:
        impulses = np.zeros(SAMPLES)
        impulses[::137] = severity * rng.uniform(1.5, 3.5, len(impulses[::137]))
        kernel = np.exp(-np.arange(100) / 15) * np.sin(2 * np.pi * 3500 * np.arange(100) / FS)
        x += np.convolve(impulses, kernel, mode="same")
    if scenario in {"shutdown", "maintenance"}:
        x = rng.normal(0, 0.001, SAMPLES)
    return {"signal": x, "features": extract(x, FS), "temperature": float(temp),
            "speed_rpm": float(rpm), "load_pct": load if rpm else 0.0,
            "torque_nm": float(load * 8) if machine_index % 5 < 2 and rpm else None,
            "operating_state": "stopped" if rpm == 0 else "running"}
