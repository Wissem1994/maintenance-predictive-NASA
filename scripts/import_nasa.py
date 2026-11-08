"""Chronological, auditable streaming feature extraction. Run as python -m scripts.import_nasa."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from ml.features.signal import extract, windows
from ml.ingestion.nasa import SAMPLE_RATE_HZ, bearing_for, discover, load_snapshot, sha256


def run(root: Path, output: Path, trial: str | None = None, limit: int | None = None,
        window_size: int = 20_480, overlap: int = 0) -> dict:
    snapshots = discover(root, trial)
    if not snapshots:
        raise ValueError("Aucun fichier NASA IMS trouvé. Voir docs/datasets.md pour l'import manuel.")
    if limit is not None and limit <= 0:
        raise ValueError("--limit doit être positif")
    selected = snapshots[:limit] if limit else snapshots
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".csv.part")
    manifest, count = [], 0
    try:
        for i, item in enumerate(selected):
            data = load_snapshot(item)
            rows = []
            digest = sha256(item.path)
            for channel in range(1, data.shape[1] + 1):
                for start, window in windows(data[:, channel - 1], window_size, overlap):
                    rows.append({
                        "dataset": "nasa_ims", "provenance": "experimental_historical",
                        "trial": item.trial, "bearing": bearing_for(item.trial, channel), "channel": channel,
                        "measured_at": item.measured_at.isoformat(), "source_file": str(item.path.resolve()),
                        "source_sha256": digest, "window_start": start, "window_size": len(window),
                        "sample_rate_hz": SAMPLE_RATE_HZ, **extract(window, SAMPLE_RATE_HZ),
                    })
            pd.DataFrame(rows).to_csv(temporary, mode="w" if i == 0 else "a", header=i == 0, index=False)
            count += len(rows)
            manifest.append({"file": str(item.path.relative_to(root)), "sha256": digest,
                             "samples": data.shape[0], "channels": data.shape[1], "trial": item.trial,
                             "measured_at": item.measured_at.isoformat()})
            if i % 100 == 0:
                print(f"{i + 1}/{len(selected)} fichiers ; {count} fenêtres", flush=True)
        if count == 0:
            raise ValueError("Aucune fenêtre complète ; réduire --window-size")
        temporary.replace(output)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    report = {
        "created_at": datetime.now(timezone.utc).isoformat(), "dataset": "nasa_ims",
        "sampling_rate_hz": SAMPLE_RATE_HZ, "timezone": "unknown_experiment_local",
        "files_discovered": len(snapshots), "files_processed": len(selected), "feature_rows": count,
        "partial_import": len(selected) < len(snapshots), "window_size": window_size, "overlap": overlap,
        "missing_policy": "reject", "unit": "source_amplitude_unverified", "files": manifest,
    }
    output.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("data/raw/nasa_ims"))
    p.add_argument("--output", type=Path, default=Path("data/processed/nasa_features.csv"))
    p.add_argument("--trial", choices=["1st_test", "2nd_test", "3rd_test"])
    p.add_argument("--limit", type=int)
    p.add_argument("--window-size", type=int, default=20_480)
    p.add_argument("--overlap", type=int, default=0)
    args = p.parse_args()
    report = run(args.root, args.output, args.trial, args.limit, args.window_size, args.overlap)
    print(json.dumps({k: v for k, v in report.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
