"""Unsupervised per-channel detection; no failure probabilities, no invented class metrics."""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import RobustScaler

from ml.features.signal import FEATURE_NAMES


def fit_detector(frame: pd.DataFrame, provenance: dict, output: Path, version: str) -> dict:
    times = sorted(frame.measured_at.unique())
    if len(times) < 80:
        raise ValueError("Au moins 80 horodatages indépendants requis pour train/calibration/test")
    train_end, calibration_end = int(len(times) * 0.2), int(len(times) * 0.3)
    training = frame[frame.measured_at.isin(times[:train_end])]
    calibration = frame[frame.measured_at.isin(times[train_end:calibration_end])]
    test = frame[frame.measured_at.isin(times[calibration_end:])]
    x = frame[FEATURE_NAMES].to_numpy(dtype=float)
    if not np.isfinite(x).all():
        raise ValueError("Caractéristiques non finies")
    scaler = RobustScaler().fit(training[FEATURE_NAMES])
    model = IsolationForest(n_estimators=150, contamination="auto", random_state=42, n_jobs=1)
    model.fit(scaler.transform(training[FEATURE_NAMES]))
    calibration_scores = -model.score_samples(scaler.transform(calibration[FEATURE_NAMES]))
    threshold = float(np.quantile(calibration_scores, 0.99))
    heldout = -model.score_samples(scaler.transform(test[FEATURE_NAMES]))
    median = training[FEATURE_NAMES].median().to_numpy()
    mad = np.median(np.abs(training[FEATURE_NAMES].to_numpy() - median), axis=0) * 1.4826
    mad = np.maximum(mad, np.maximum(np.abs(median) * 0.01, 1e-8))
    statistical = np.max(np.abs((test[FEATURE_NAMES].to_numpy() - median) / mad), axis=1)
    metadata = {
        "version": version, "algorithm": "IsolationForest + baseline robuste MAD", "provenance": provenance,
        "trained_at": datetime.now(timezone.utc).isoformat(), "features": FEATURE_NAMES,
        "configuration": {"n_estimators": 150, "random_state": 42, "calibration_quantile": 0.99},
        "split": {"method": "chronologique par fichier, 20/10/70 ; aucune fenêtre du même fichier partagée",
                  "training_end": str(times[train_end - 1]), "calibration_end": str(times[calibration_end - 1]),
                  "train_rows": len(training), "calibration_rows": len(calibration), "test_rows": len(test)},
        "threshold": threshold,
        "metrics": {"heldout_anomaly_fraction": float((heldout > threshold).mean()),
                    "baseline_exceedance_fraction": float((statistical > 6).mean()),
                    "test_score_min": float(heldout.min()), "test_score_max": float(heldout.max()),
                    "test_score_median": float(np.median(heldout)), "precision": None, "recall": None,
                    "f1": None, "pr_auc": None, "false_alarms_per_hour": None,
                    "detection_lead_time_hours": None, "calibration_error": None},
        "score_histogram": {"counts": np.histogram(heldout, bins=12)[0].tolist(),
                            "edges": np.histogram(heldout, bins=12)[1].tolist()},
        "limitations": [
            "Début d'essai supposé nominal, sans confirmation d'absence de défaut latent.",
            "Holdout du même essai : aucune validation de généralisation sur nouvelle machine.",
            "Absence d'étiquettes par fichier : precision/recall/PR-AUC et faux positifs non calculables.",
            "Score élevé = atypique par rapport au début de cet essai ; pas une probabilité de panne.",
            "Seuil empirique de démonstration, non validé industriellement.",
        ],
        "runtime": {"python": platform.python_version(), "sklearn": sklearn.__version__},
    }
    bundle = {"scaler": scaler, "model": model, "median": median, "mad": mad,
              "metadata": metadata, "calibration_scores": np.sort(calibration_scores)}
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, output / f"{version}.joblib")
    (output / f"{version}.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return metadata


def infer(bundle: dict, features: dict) -> dict:
    row = pd.DataFrame([[features[name] for name in FEATURE_NAMES]], columns=FEATURE_NAMES)
    if not np.isfinite(row.to_numpy()).all():
        raise ValueError("Caractéristiques invalides pour l'inférence")
    raw = float(-bundle["model"].score_samples(bundle["scaler"].transform(row))[0])
    baseline = float(np.max(np.abs((row.to_numpy()[0] - bundle["median"]) / bundle["mad"])))
    threshold = bundle["metadata"]["threshold"]
    return {"anomaly_score": raw, "threshold": threshold, "baseline_z": baseline,
            "is_anomaly": raw > threshold, "risk": "élevé" if raw > threshold and baseline > 6
            else "à surveiller" if raw > threshold else "nominal",
            "health_index": None, "failure_probability": None, "model_version": bundle["metadata"]["version"]}
