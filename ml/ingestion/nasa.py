"""NASA IMS ASCII snapshots. Never infer acquisition time from filesystem metadata."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

TIMESTAMP = re.compile(r"^\d{4}(?:\.\d{2}){5}$")
SAMPLE_RATE_HZ = 20_000.0  # Source: IMS readme; 20480 samples => 1.024 s, not exactly 1 s.
CHANNELS = {"1st_test": 8, "2nd_test": 4, "3rd_test": 4}


@dataclass(frozen=True)
class Snapshot:
    path: Path
    trial: str
    measured_at: datetime  # Local experiment clock; timezone is undocumented, DO NOT mark UTC.


def trial_for(path: Path) -> str:
    for part in path.parts:
        if part in CHANNELS:
            return part
    if "4th_test" in path.parts:  # Packaging alias for set 3; preserve original path.
        return "3rd_test"
    raise ValueError(f"Essai non identifiable : {path}. Conserver 1st_test, 2nd_test ou 3rd_test.")


def discover(root: Path, trial: str | None = None) -> list[Snapshot]:
    snapshots: list[Snapshot] = []
    if not root.exists():
        return snapshots
    for path in root.rglob("*"):
        if path.is_file() and TIMESTAMP.fullmatch(path.name):
            name = trial_for(path)
            if trial is None or name == trial:
                snapshots.append(Snapshot(path, name, datetime.strptime(path.name, "%Y.%m.%d.%H.%M.%S")))
    snapshots.sort(key=lambda s: (s.measured_at, s.trial, str(s.path)))
    keys = [(s.trial, s.measured_at) for s in snapshots]
    if len(keys) != len(set(keys)):
        raise ValueError("Horodatages dupliqués dans un essai : vérifier les copies des données brutes.")
    return snapshots


def load_snapshot(snapshot: Snapshot, strict_length: bool = True) -> NDArray[np.float64]:
    data = np.loadtxt(snapshot.path, dtype=np.float64, ndmin=2)
    expected = CHANNELS[snapshot.trial]
    if data.shape[1] != expected:
        raise ValueError(f"{snapshot.path}: {data.shape[1]} canaux au lieu de {expected}")
    if strict_length and data.shape[0] != 20_480:
        raise ValueError(f"{snapshot.path}: {data.shape[0]} échantillons au lieu de 20480")
    if data.shape[0] < 8 or not np.isfinite(data).all():
        raise ValueError(f"{snapshot.path}: signal trop court ou valeurs absentes/non finies")
    return data


def bearing_for(trial: str, channel: int) -> int:
    if trial not in CHANNELS or not 1 <= channel <= CHANNELS[trial]:
        raise ValueError("Canal invalide pour cet essai")
    return (channel + 1) // 2 if trial == "1st_test" else channel


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
