"""Train an explicitly synthetic nominal detector. Never combine with NASA experimental data."""
from pathlib import Path
import pandas as pd
from ml.training.anomaly import fit_detector
from simulation.industrial import generate


def main():
    rows = []
    # Twenty machines per timestamp, kept together across chronological splits.
    for tick in range(100):
        for i in range(20):
            data = generate(42, i, tick)
            rows.append({**data["features"], "measured_at": f"{tick:06}"})
    meta = fit_detector(pd.DataFrame(rows), {"dataset": "industrial_simulation", "type": "synthetic",
                        "seed": 42, "generator": "simulation.industrial.generate"}, Path("artifacts"),
                        "simulation-nominal-v1")
    meta["limitations"] = [
        "Entraînement et test sur données entièrement synthétiques du même générateur.",
        "Séparation chronologique par cycle ; toutes les machines d'un cycle restent ensemble.",
        "Référence nominale connue par construction ; aucune mesure de performance industrielle.",
        "Modèle jamais appliqué aux mesures NASA ; score non probabiliste.",
        "Démarrage thermique et variations de charge simplifiés ; aucune validation de jumeau numérique."
    ]
    import joblib
    import json
    path = Path("artifacts/simulation-nominal-v1.joblib")
    bundle = joblib.load(path)
    bundle["metadata"] = meta
    joblib.dump(bundle, path)
    path.with_suffix(".json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Modèle synthétique nominal sauvegardé", meta["metrics"])


if __name__ == "__main__":
    main()
