import argparse
import json
from pathlib import Path

import pandas as pd

from ml.ingestion.nasa import sha256
from ml.training.anomaly import fit_detector


def main():
    p = argparse.ArgumentParser(description="Entraîner les détecteurs NASA par essai et canal")
    p.add_argument("--features", type=Path, default=Path("data/processed/nasa_features.csv"))
    p.add_argument("--output", type=Path, default=Path("artifacts"))
    args = p.parse_args()
    frame = pd.read_csv(args.features)
    if not frame.dataset.eq("nasa_ims").all() or not frame.provenance.eq("experimental_historical").all():
        raise ValueError("Ce script accepte uniquement le pipeline NASA expérimental")
    source_hash = sha256(args.features)
    for (trial, channel), group in frame.groupby(["trial", "channel"]):
        version = f"nasa-{trial}-ch{channel}-{source_hash[:10]}"
        meta = fit_detector(group, {"dataset": "nasa_ims", "type": "experimental_historical",
                            "trial": trial, "channel": int(channel), "features_sha256": source_hash},
                            args.output, version)
        print(json.dumps({"version": version, "metrics": meta["metrics"]}, indent=2))


if __name__ == "__main__":
    main()
