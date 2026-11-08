
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_replay_persistence_history_and_origin(client, app_config):
    assert client.get("/api/health").json()["status"] == "ok"
    assert client.get("/api/datasets").json()["nasa_ims"]["trials"][0]["files"] == 3
    assert client.get("/api/machines").json()["total"] == 4
    response = client.post("/api/replay/start", json={"trial": "2nd_test", "channel": 1, "speed": 60})
    assert response.status_code == 200
    engine = client.app.state.engine
    engine._replay_tick()
    mid = response.json()["machine_id"]
    measurements = client.get(f"/api/machines/{mid}/measurements").json()
    assert measurements["total"] == 1
    assert measurements["items"][0]["temperature"] is None
    assert measurements["items"][0]["provenance"] == "experimental_historical"
    assert client.get(f"/api/machines/{mid}/signal").json()["sample_count"] == 20480
    assert client.get(f"/api/machines/{mid}/predictions").json()["total"] == 0  # No fake model.
    assert client.post("/api/replay/pause").json()["status"] == "paused"
    assert client.post("/api/replay/resume").json()["status"] == "running"
    assert client.post("/api/replay/stop").json()["status"] == "stopped"
    assert client.post("/api/replay/reset").json()["cursor"] == 0
    with TestClient(create_app(app_config, background=False)) as restarted:
        assert restarted.get(f"/api/machines/{mid}/measurements").json()["total"] == 1
        assert restarted.get("/api/engine").json()["status"] == "stopped"


def test_alert_lifecycle_dedup_and_maintenance(client):
    client.post("/api/simulation/start", json={"seed": 42, "machine_count": 20})
    engine = client.app.state.engine
    assert client.get("/api/machines?mode=simulation").json()["total"] == 20
    for mid in ("sim-01",):
        engine.scenarios[mid] = ("degradation", -30)
    for _ in range(6):
        engine._simulation_tick()
    alerts = client.get("/api/alerts?mode=simulation&machine_id=sim-01").json()["items"]
    vibration = [a for a in alerts if a["rule"] == "vibration"]
    assert len(vibration) == 1
    alert_id = vibration[0]["id"]
    assert client.post(f"/api/alerts/{alert_id}/acknowledge").json()["acknowledged_at"]
    assert client.post(f"/api/alerts/{alert_id}/resolve").json()["resolved_at"]
    assert client.post(f"/api/alerts/{alert_id}/acknowledge").status_code == 409
    # Resolving does not spam a new alert during cooldown.
    engine._simulation_tick()
    assert client.get("/api/alerts?mode=simulation&machine_id=sim-01").json()["total"] == len(alerts)
    body = {"machine_id": "sim-01", "reason": "Inspection du roulement", "priority": "high", "comments": "Planifié"}
    response = client.post("/api/maintenance", json=body)
    assert response.status_code == 201
    event = response.json()
    assert client.patch(f"/api/maintenance/{event['id']}", json={"status": "completed", "comments": "Remplacé"}).json()["status"] == "completed"
    assert client.get("/api/maintenance?mode=simulation").json()["total"] == 1
    assert client.get("/api/maintenance?mode=nasa").json()["total"] == 0
    assert client.get("/api/alerts?mode=nasa").json()["total"] == 0
    assert client.get("/api/machines/sim-01/signal").json()["provenance"] == "synthetic"


def test_hysteresis_auto_resolution(client):
    client.post("/api/simulation/start", json={"machine_count": 1})
    engine = client.app.state.engine
    engine.scenarios["sim-01"] = ("vibration", -30)
    for _ in range(3):
        engine._simulation_tick()
    assert client.get("/api/alerts?mode=simulation&status=open").json()["total"] == 1
    engine.scenarios["sim-01"] = ("normal", engine.state["tick"])
    for _ in range(3):
        engine._simulation_tick()
    assert client.get("/api/alerts?mode=simulation&status=resolved").json()["total"] == 1


def test_invalid_parameters(client):
    assert client.get("/api/machines/absent").status_code == 404
    assert client.get("/api/machines?limit=-1").status_code == 422
    assert client.post("/api/simulation/start", json={"machine_count": 21}).status_code == 422
    assert client.post("/api/replay/start", json={"trial": "2nd_test", "channel": 8}).status_code == 409
    assert client.post("/api/replay/start", json={"trial": "1st_test", "channel": 1}).status_code == 409
    assert client.post("/api/maintenance", json={"machine_id": "absent", "reason": "Test"}).status_code == 404


def test_websocket_real_engine_updates(app_config):
    app = create_app(app_config, background=True)
    with TestClient(app) as client, client.websocket_connect("/ws", headers={"origin": "http://localhost:5173"}) as ws:
        assert ws.receive_json()["type"] == "state"
        assert client.post("/api/simulation/start", json={"machine_count": 1}).status_code == 200
        assert ws.receive_json()["type"] == "state"
        assert ws.receive_json()["type"] == "update"
        assert client.get("/api/machines/sim-01/measurements").json()["total"] >= 1
        client.post("/api/replay/stop")


def test_absence_monitor_respects_expected_time_and_deduplicates(client):
    import time
    client.post("/api/simulation/start", json={"machine_count": 1})
    engine = client.app.state.engine
    engine._simulation_tick()
    engine.next_due = time.monotonic() + 600
    assert engine._check_stale() == 0
    engine.next_due = time.monotonic() - 100
    assert engine._check_stale() == 1
    assert engine._check_stale() == 0
    engine._simulation_tick()
    assert client.get("/api/alerts?mode=simulation&status=resolved").json()["total"] == 1


def test_summary_counts_full_history_beyond_list_limit(client):
    from backend.app.models.entities import Alert
    from backend.app.services.alerts import utcnow
    with client.app.state.sessions() as db:
        db.add_all([Alert(machine_id="nasa-2nd_test-ch1", rule="test", severity="critical",
                          message="Count fixture", triggered_values={}, created_at=utcnow()) for _ in range(205)])
        db.commit()
    summary = client.get("/api/summary?mode=nasa").json()
    assert summary["machines"] == 4
    assert summary["unacknowledged"] == 205
    assert summary["critical_active"] == 205
    assert client.get("/api/alerts?mode=nasa&limit=50").json()["total"] == 205
    assert client.get("/api/summary?mode=simulation").json()["unacknowledged"] == 0
