import numpy as np
import pytest

from ml.features.signal import clean, extract, spectrum, windows


def test_sinusoid_features_and_spectrum():
    fs = 20_000
    x = 2 * np.sin(2 * np.pi * 1000 * np.arange(fs) / fs)
    f = extract(x, fs)
    assert f["rms"] == pytest.approx(np.sqrt(2))
    assert f["variance"] == pytest.approx(2)
    assert f["kurtosis"] == pytest.approx(1.5)
    assert f["skewness"] == pytest.approx(0, abs=1e-12)
    assert f["crest_factor"] == pytest.approx(np.sqrt(2))
    assert f["energy"] == pytest.approx(2 * fs)
    freq, amplitude = spectrum(x, fs)
    assert freq[amplitude.argmax()] == 1000
    assert amplitude.max() == pytest.approx(2)
    assert sum(f[k] for k in ("band_low", "band_mid", "band_high")) == pytest.approx(2)


def test_constant_and_zero_are_finite():
    for x in (np.zeros(100), np.ones(100)):
        assert all(np.isfinite(v) for v in extract(x, 1000).values())
    assert extract(np.zeros(100), 1000)["crest_factor"] == 0


def test_missing_policy_and_windows():
    x = np.ones(1000)
    x[5] = np.nan
    with pytest.raises(ValueError):
        clean(x)
    assert clean(x, "interpolate")[5] == 1
    x[0] = np.nan
    with pytest.raises(ValueError):
        clean(x, "interpolate")
    pieces = list(windows(np.arange(100), size=32, overlap=16))
    assert [i for i, _ in pieces] == [0, 16, 32, 48, 64]
    with pytest.raises(ValueError):
        list(windows(np.arange(100), size=32, overlap=32))


def test_noise_moments():
    x = np.random.default_rng(42).normal(size=200_000)
    f = extract(x, 20_000)
    assert f["rms"] == pytest.approx(1, abs=0.01)
    assert f["kurtosis"] == pytest.approx(3, abs=0.05)
