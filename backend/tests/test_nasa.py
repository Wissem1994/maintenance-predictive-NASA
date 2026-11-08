from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from ml.ingestion.nasa import bearing_for, discover, load_snapshot
from scripts.import_nasa import run


def test_import_chronology_and_lineage(tmp_path):
    # Synthetic format fixture only. NEVER treated as downloaded NASA measurements.
    root = tmp_path / "fixture" / "2nd_test"
    root.mkdir(parents=True)
    for name in ["2004.02.12.10.42.39", "2004.02.12.10.32.39"]:
        np.savetxt(root / name, np.ones((20480, 4)))
    snapshots = discover(root.parent)
    assert snapshots[0].path.name == "2004.02.12.10.32.39"
    assert snapshots[0].measured_at.tzinfo is None
    assert load_snapshot(snapshots[0]).shape == (20480, 4)
    output = tmp_path / "features.csv"
    report = run(root.parent, output)
    frame = pd.read_csv(output)
    assert report["feature_rows"] == 8
    assert frame.window_start.eq(0).all()
    assert frame.source_sha256.str.len().eq(64).all()
    assert frame.duration_seconds.eq(1.024).all()
    assert bearing_for("1st_test", 5) == 3
    with pytest.raises(ValueError):
        bearing_for("2nd_test", 5)


def test_reject_bad_channels_and_duplicate_files(tmp_path):
    root = tmp_path / "2nd_test"
    root.mkdir()
    name = "2004.02.12.10.32.39"
    np.savetxt(root / name, np.ones((8, 2)))
    with pytest.raises(ValueError):
        load_snapshot(discover(tmp_path)[0])
    copy = root / "copy"
    copy.mkdir()
    np.savetxt(copy / name, np.ones((8, 2)))
    with pytest.raises(ValueError, match="dupliqués"):
        discover(tmp_path)


def test_real_nasa_if_imported():
    items = discover(Path("data/raw/nasa_ims"))
    if not items:
        pytest.skip("Données NASA réelles non importées dans cet environnement")
    data = load_snapshot(items[0])
    assert data.shape[0] == 20480
    assert np.isfinite(data).all()
