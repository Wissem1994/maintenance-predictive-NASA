import numpy as np
import pandas as pd
import pytest

from ml.training.anomaly import fit_detector, infer
from simulation.industrial import generate


def test_reproducible_simulation_and_scenarios():
    config = dict(seed=42, machine_index=0, tick=100)
    a, b = generate(**config), generate(**config)
    assert np.array_equal(a["signal"], b["signal"])
    bad = generate(**config, scenario="degradation", age=25)
    assert bad["features"]["rms"] > 4 * a["features"]["rms"]
    assert generate(**config, scenario="shutdown")["speed_rpm"] == 0
    assert generate(**config, scenario="overheating", age=40)["temperature"] > a["temperature"] + 50
    assert generate(**config, scenario="maintenance")["operating_state"] == "stopped"
    with pytest.raises(ValueError):
        generate(**config, scenario="invented")


def test_model_roundtrip_chronology_and_no_probability(tmp_path):
    rows = []
    for tick in range(100):
        data = generate(42, 0, tick)
        rows.append({**data["features"], "measured_at": f"{tick:04}"})
    frame = pd.DataFrame(rows)
    meta = fit_detector(frame, {"dataset": "test_synthetic"}, tmp_path, "unit-test")
    import joblib
    bundle = joblib.load(tmp_path / "unit-test.joblib")
    result = infer(bundle, generate(42, 0, 101)["features"])
    assert np.isfinite(result["anomaly_score"])
    assert result["failure_probability"] is None
    assert result["health_index"] is None
    assert meta["metrics"]["f1"] is None
    assert meta["split"]["training_end"] < meta["split"]["calibration_end"]
    assert meta["split"]["train_rows"] == 20
    assert (tmp_path / "unit-test.json").exists()
