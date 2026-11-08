
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.database.session import Base, make_database
from backend.app.main import create_app
from backend.app.models import entities  # noqa: F401


@pytest.fixture
def app_config(tmp_path):
    raw = tmp_path / "raw" / "2nd_test"
    raw.mkdir(parents=True)
    x = np.arange(20480) / 20_000
    values = np.column_stack([0.1 * np.sin(2 * np.pi * (800 + i * 100) * x) for i in range(4)])
    for name in ["2004.02.12.10.32.39", "2004.02.12.10.42.39", "2004.02.12.10.52.39"]:
        np.savetxt(raw / name, values)
    config = Settings(database_url=f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
                      raw_dir=raw.parent, artifact_dir=tmp_path / "artifacts", tick_seconds=0.05)
    engine, _ = make_database(config.database_url)
    Base.metadata.create_all(engine)
    engine.dispose()
    return config


@pytest.fixture
def client(app_config):
    app = create_app(app_config, background=False)
    with TestClient(app) as client:
        yield client
