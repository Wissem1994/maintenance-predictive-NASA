from pathlib import Path
import time

from fastapi import WebSocketDisconnect
import joblib
import pandas as pd
import pytest


def test_replay_historical_gap_and_speed_change_while_paused(client):
    client.post("/api/replay/start", json={"trial": "2nd_test", "channel": 1, "speed": 60})
    engine = client.app.state.engine
    engine._replay_tick()
    assert engine._historical_gap() == 600
    engine.next_due = time.monotonic() + 60
    client.post("/api/replay/pause")
    old_remaining = engine.state["remaining_seconds"]
    assert client.post("/api/replay/speed", json={"speed": 10}).status_code == 200
    assert engine.state["remaining_seconds"] == pytest.approx(old_remaining * 6)
    client.post("/api/replay/resume")
    assert 358 <= engine.next_due - time.monotonic() <= 361
    client.post("/api/replay/stop")


def test_websocket_rejects_foreign_origin(client):
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/ws", headers={"origin": "https://untrusted.invalid"}):
            pass
    assert exc.value.code == 1008


def test_ai4i_saved_model_has_no_target_leakage_and_consistent_metrics():
    artifact = Path("artifacts/ai4i-rf-calibrated-v1.joblib")
    csv = Path("data/raw/ai4i/ai4i2020.csv")
    if not artifact.exists() or not csv.exists():
        pytest.skip("Importer et entraîner le complément AI4I pour ce contrôle d'intégration")
    bundle = joblib.load(artifact)
    meta = bundle["metadata"]
    assert not {"Machine failure", "TWF", "HDF", "PWF", "OSF", "RNF", "UDI", "Product ID"} & set(meta["features"])
    assert meta["provenance"]["type"] == "synthetic"
    assert meta["task"] == "current_state_classification"
    tn, fp = meta["confusion_matrix"][0]
    fn, tp = meta["confusion_matrix"][1]
    assert tn + fp + fn + tp == 2000
    assert meta["metrics"]["f1"] == pytest.approx(2 * tp / (2 * tp + fp + fn))
    data = pd.read_csv(csv)
    probability = bundle["classifier"].predict_proba(data[meta["features"]].tail(5))[:, 1]
    assert ((probability >= 0) & (probability <= 1)).all()
