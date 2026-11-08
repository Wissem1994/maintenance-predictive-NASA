"""Generate actual-data figures and inventory, without labelling entire lifetimes as healthy/faulty."""
import argparse
import json
from pathlib import Path

import os
os.environ.setdefault('MPLCONFIGDIR', str(Path('.cache/matplotlib').resolve()))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from ml.features.signal import spectrum
from ml.ingestion.nasa import SAMPLE_RATE_HZ, discover, load_snapshot


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=Path("data/raw/nasa_ims"))
    p.add_argument("--features", type=Path, default=Path("data/processed/nasa_features.csv"))
    p.add_argument("--output", type=Path, default=Path("docs/reports"))
    args = p.parse_args()
    items = discover(args.root)
    if not items:
        raise ValueError("Aucun fichier réel : importer NASA IMS avant l'exploration")
    args.output.mkdir(parents=True, exist_ok=True)
    inventory = {}
    for trial in sorted({s.trial for s in items}):
        subset = [s for s in items if s.trial == trial]
        times = pd.Series([s.measured_at for s in subset])
        gaps = times.diff().dt.total_seconds().dropna()
        inventory[trial] = {"files": len(subset), "first": times.min().isoformat(),
                            "last": times.max().isoformat(), "median_interval_s": float(gaps.median())
                            if len(gaps) else None, "max_interval_s": float(gaps.max()) if len(gaps) else None}
    first = items[0]
    x = load_snapshot(first)[:, 0]
    f, a = spectrum(x, SAMPLE_RATE_HZ)
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), constrained_layout=True)
    axes[0].plot([i / SAMPLE_RATE_HZ for i in range(len(x))], x, linewidth=0.4)
    axes[0].set(xlabel="Temps dans le fichier (s)", ylabel="Amplitude source (unité à vérifier)",
                title=f"NASA IMS réel — {first.trial} — canal 1 — {first.path.name}")
    axes[1].plot(f, a, linewidth=0.6)
    axes[1].set(xlabel="Fréquence (Hz)", ylabel="Amplitude crête — FFT Hann")
    fig.savefig(args.output / "nasa_signal_fft.png", dpi=150)
    plt.close(fig)
    if args.features.exists():
        frame = pd.read_csv(args.features)
        frame["measured_at"] = pd.to_datetime(frame["measured_at"])
        fig, ax = plt.subplots(figsize=(11, 4), constrained_layout=True)
        for (trial, channel), group in frame.groupby(["trial", "channel"]):
            ax.plot(group.measured_at, group.rms, label=f"{trial} · ch {channel}", linewidth=0.8)
        ax.set(xlabel="Horodatage expérimental (fuseau inconnu)", ylabel="RMS (unité source)",
               title="NASA IMS — évolution des mesures importées")
        ax.legend(ncol=4, fontsize=7)
        fig.savefig(args.output / "nasa_rms_trend.png", dpi=150)
        plt.close(fig)
    (args.output / "nasa_inventory.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    print(json.dumps(inventory, indent=2))


if __name__ == "__main__":
    main()
