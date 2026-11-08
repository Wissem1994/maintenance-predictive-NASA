"""AI4I: classification of the PRESENT synthetic failure state, not a future failure forecast."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import urllib.request
import zipfile

import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.frozen import FrozenEstimator
from sklearn.metrics import average_precision_score, brier_score_loss, confusion_matrix, precision_recall_fscore_support
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import OneHotEncoder

from ml.ingestion.nasa import sha256

FEATURES = ["Type", "Air temperature [K]", "Process temperature [K]", "Rotational speed [rpm]",
            "Torque [Nm]", "Tool wear [min]"]
URL = "https://archive.ics.uci.edu/static/public/601/ai4i+2020+predictive+maintenance+dataset.zip"


def train(csv: Path, output: Path) -> dict:
    data = pd.read_csv(csv).sort_values("UDI").reset_index(drop=True)
    if len(data) < 100 or data[FEATURES + ["Machine failure"]].isna().any().any():
        raise ValueError("AI4I incomplet ou valeurs manquantes")
    if data.UDI.duplicated().any() or not set(data["Machine failure"].unique()) <= {0, 1}:
        raise ValueError("Identifiants ou cibles invalides")
    x, y = data[FEATURES], data["Machine failure"]
    n_train, n_cal = int(len(data) * 0.6), int(len(data) * 0.8)
    model = make_pipeline(ColumnTransformer([("type", OneHotEncoder(handle_unknown="ignore"), ["Type"])],
                                           remainder="passthrough"),
                          RandomForestClassifier(n_estimators=200, min_samples_leaf=3, max_depth=12,
                                                 class_weight="balanced_subsample", random_state=42, n_jobs=1))
    model.fit(x.iloc[:n_train], y.iloc[:n_train])
    if y.iloc[n_train:n_cal].nunique() != 2 or y.iloc[n_cal:].nunique() != 2:
        raise ValueError("Calibration et test doivent contenir les deux classes")
    calibrated = CalibratedClassifierCV(FrozenEstimator(model), method="sigmoid")
    calibrated.fit(x.iloc[n_train:n_cal], y.iloc[n_train:n_cal])
    probability = calibrated.predict_proba(x.iloc[n_cal:])[:, 1]
    target = y.iloc[n_cal:]
    baseline = DummyClassifier(strategy="prior").fit(x.iloc[:n_train], y.iloc[:n_train])

    def evaluate(prob):
        precision, recall, f1, _ = precision_recall_fscore_support(target, prob >= 0.5, average="binary",
                                                                  zero_division=0)
        return {"precision": float(precision), "recall": float(recall), "f1": float(f1),
                "pr_auc": float(average_precision_score(target, prob)),
                "brier_score": float(brier_score_loss(target, prob)),
                "confusion_matrix": confusion_matrix(target, prob >= 0.5, labels=[0, 1]).tolist()}
    observed, predicted = calibration_curve(target, probability, n_bins=5, strategy="uniform")
    metrics = evaluate(probability)
    matrix = metrics.pop("confusion_matrix")
    metadata = {
        "version": "ai4i-rf-calibrated-v1", "algorithm": "Random Forest + calibration sigmoïde",
        "task": "current_state_classification", "trained_at": datetime.now(timezone.utc).isoformat(),
        "provenance": {"dataset": "ai4i_2020", "type": "synthetic", "source": URL,
                       "source_sha256": sha256(csv), "rows": len(data)},
        "features": FEATURES, "threshold": 0.5, "metrics": metrics, "confusion_matrix": matrix,
        "baseline_metrics": evaluate(baseline.predict_proba(x.iloc[n_cal:])[:, 1]),
        "calibration_curve": {"predicted": predicted.tolist(), "observed": observed.tolist()},
        "split": {"method": "UDI ordonnés 60/20/20 ; entraînement, calibration et test disjoints",
                  "train_rows": n_train, "calibration_rows": n_cal - n_train, "test_rows": len(data) - n_cal},
        "configuration": {"n_estimators": 200, "random_state": 42, "classification_threshold": 0.5},
        "limitations": [
            "Dataset entièrement synthétique, distinct des vibrations NASA et du simulateur local.",
            "Cible : machine en panne sur cette ligne ; aucun horizon futur ni RUL.",
            "Ordre UDI conservé, sans prétendre disposer d'horodatages ni d'identités réelles de machines.",
            "Calibration et métriques évaluées uniquement dans le domaine synthétique AI4I.",
            "Les cinq modes de panne et les identifiants sont exclus des entrées pour éviter la fuite de cible.",
            "Probabilités jamais appliquées aux machines NASA ou au simulateur."
        ],
        "score_histogram": {"counts": np.histogram(probability, bins=10, range=(0, 1))[0].tolist(),
                            "edges": np.linspace(0, 1, 11).tolist()},
    }
    output.mkdir(parents=True, exist_ok=True)
    joblib.dump({"classifier": calibrated, "metadata": metadata}, output / "ai4i-rf-calibrated-v1.joblib")
    (output / "ai4i-rf-calibrated-v1.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False),
                                                     encoding="utf-8")
    return metadata


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--csv", type=Path, default=Path("data/raw/ai4i/ai4i2020.csv"))
    p.add_argument("--archive", type=Path, default=Path("data/archives/ai4i.zip"))
    p.add_argument("--download", action="store_true")
    args = p.parse_args()
    if args.download and not args.archive.exists():
        args.archive.parent.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL, timeout=60) as response:
            args.archive.write_bytes(response.read())
    if not args.csv.exists() and args.archive.exists():
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(args.archive) as archive:
            candidates = [name for name in archive.namelist() if Path(name).name == "ai4i2020.csv"]
            if len(candidates) != 1:
                raise ValueError("CSV AI4I non identifiable dans l'archive")
            args.csv.write_bytes(archive.read(candidates[0]))
    meta = train(args.csv, Path("artifacts"))
    Path("docs/reports/ai4i_validation.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"metrics": meta["metrics"], "confusion_matrix": meta["confusion_matrix"],
                      "baseline_metrics": meta["baseline_metrics"]}, indent=2))


if __name__ == "__main__":
    main()
