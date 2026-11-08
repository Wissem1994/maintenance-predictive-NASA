"""Explicit conventions: population moments, Pearson kurtosis, raw RMS, Hann FFT."""
from __future__ import annotations

from collections.abc import Iterator

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import signal, stats

FEATURE_NAMES = ["rms", "std", "kurtosis", "skewness", "peak_to_peak", "crest_factor",
                 "band_low", "band_mid", "band_high"]


def clean(values: ArrayLike, missing: str = "reject") -> NDArray[np.float64]:
    x = np.asarray(values, dtype=np.float64)
    if x.ndim != 1 or len(x) < 8:
        raise ValueError("Un signal doit être un vecteur d'au moins 8 échantillons")
    if missing not in {"reject", "interpolate"}:
        raise ValueError("Politique de valeurs manquantes inconnue")
    finite = np.isfinite(x)
    if not finite.all():
        if missing == "reject" or finite.mean() < 0.99 or not finite[0] or not finite[-1]:
            raise ValueError("Valeurs non finies : rejet ; interpolation limitée à 1 % et hors extrémités")
        x = np.interp(np.arange(len(x)), np.flatnonzero(finite), x[finite])
    return x


def windows(values: ArrayLike, size: int = 4096, overlap: int = 0) -> Iterator[tuple[int, NDArray]]:
    x = clean(values)
    if size < 8 or not 0 <= overlap < size:
        raise ValueError("Fenêtrage invalide")
    for start in range(0, len(x) - size + 1, size - overlap):
        yield start, x[start:start + size]  # Discard short final window, never pad with invented samples.


def spectrum(values: ArrayLike, fs: float) -> tuple[NDArray, NDArray]:
    x = clean(values)
    if not np.isfinite(fs) or fs <= 0:
        raise ValueError("Fréquence d'échantillonnage invalide")
    win = signal.windows.hann(len(x), sym=False)
    amplitude = np.abs(np.fft.rfft((x - x.mean()) * win)) / win.sum()
    amplitude[1:-1 if len(x) % 2 == 0 else None] *= 2
    return np.fft.rfftfreq(len(x), 1 / fs), amplitude


def extract(values: ArrayLike, fs: float) -> dict[str, float]:
    x = clean(values)
    freq, amp = spectrum(x, fs)
    rms = float(np.sqrt(np.mean(x * x)))
    variance = float(np.var(x))
    f, psd = signal.periodogram(x, fs=fs, window="hann", detrend="constant", scaling="density")
    df = fs / len(x)
    bands = (("low", 0, 1000), ("mid", 1000, 5000), ("high", 5000, fs / 2))
    peaks, _ = signal.find_peaks(amp)
    peaks = peaks[np.argsort(amp[peaks])[::-1]][:3]
    result = {
        "mean": float(x.mean()), "rms": rms, "std": float(x.std()), "variance": variance,
        "kurtosis": float(stats.kurtosis(x, fisher=False, bias=True)) if variance > 1e-24 else 0.0,
        "skewness": float(stats.skew(x, bias=True)) if variance > 1e-24 else 0.0,
        "peak_to_peak": float(np.ptp(x)), "crest_factor": float(np.max(np.abs(x)) / rms) if rms else 0.0,
        "energy": float(np.sum(x * x)), "duration_seconds": len(x) / fs,
    }
    for name, lo, hi in bands:
        mask = (f >= lo) & ((f <= hi) if hi == fs / 2 else (f < hi))
        result[f"band_{name}"] = float(psd[mask].sum() * df) if hi > lo else 0.0
    for i in range(3):
        result[f"dominant_frequency_{i + 1}"] = float(freq[peaks[i]]) if i < len(peaks) else 0.0
    return result


def preview(values: ArrayLike, fs: float, max_points: int = 512) -> dict:
    x = clean(values)
    freq, amp = spectrum(x, fs)
    # Min/max buckets preserve transients; FFT uses max buckets so narrow peaks remain visible.
    step = max(1, int(np.ceil(len(x) / (max_points // 2))))
    indices = []
    for start in range(0, len(x), step):
        block = x[start:start + step]
        indices.extend(sorted({start + int(block.argmin()), start + int(block.argmax())}))
    fstep = max(1, int(np.ceil(len(freq) / max_points)))
    bins = [start + int(amp[start:start + fstep].argmax()) for start in range(0, len(freq), fstep)]
    return {
        "signal": [{"time": i / fs, "value": float(x[i])} for i in indices],
        "spectrum": [{"frequency": float(freq[i]), "amplitude": float(amp[i])} for i in bins],
        "sample_rate_hz": fs, "sample_count": len(x), "features": extract(x, fs),
    }
