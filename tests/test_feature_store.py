import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest
from feast import FeatureStore
from feast.repo_config import load_repo_config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import generate_data  # noqa: E402
import online_features  # noqa: E402
import training_dataset  # noqa: E402

LOCAL_CONFIG = """
project: driver_stats
provider: local
registry: {repo}/registry.db
online_store:
  type: sqlite
  path: {repo}/online.db
offline_store:
  type: file
entity_key_serialization_version: 2
"""


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    repo = tmp_path_factory.mktemp("repo")
    shutil.copy(ROOT / "feature_repo" / "features.py", repo / "features.py")
    (repo / "feature_store.yaml").write_text(LOCAL_CONFIG.format(repo=repo))
    data = repo / "data"
    data.mkdir()
    end = datetime.now(UTC)
    generate_data.generate(drivers=5, hours=24, end=end).to_parquet(data / "driver_hourly_stats.parquet")

    import os

    os.environ["FEAST_DATA_ROOT"] = str(data)
    fs = FeatureStore(repo_path=str(repo))
    import features

    fs.apply([features.driver, features.driver_hourly_stats, features.driver_activity_v1])
    fs.materialize(start_date=end - timedelta(days=2), end_date=end + timedelta(minutes=1))
    return fs


def test_production_config_expands_environment(monkeypatch):
    monkeypatch.setenv("FEAST_BUCKET", "my-bucket")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    config = load_repo_config(ROOT / "feature_repo", ROOT / "feature_repo" / "feature_store.yaml")
    assert config.registry.path == "s3://my-bucket/registry/registry.db"
    assert config.online_store.type == "dynamodb"
    assert config.online_store.region == "eu-west-1"


def test_generated_data_shape():
    df = generate_data.generate(drivers=3, hours=10)
    assert len(df) == 30
    assert df["conv_rate"].between(0, 1).all()


def test_online_features_return_latest_values(store):
    result = online_features.fetch(store, [1001, 1002])
    assert result["driver_id"] == [1001, 1002]
    assert all(v is not None for v in result["conv_rate"])


def test_training_dataset_is_point_in_time_correct(store):
    now = datetime.now(UTC)
    entity_df = pd.DataFrame(
        {
            "driver_id": [1001, 1001, 1003],
            "event_timestamp": [now - timedelta(hours=3), now - timedelta(hours=10), now - timedelta(hours=5)],
            "label": [1, 0, 1],
        }
    )
    dataset = training_dataset.build(store, entity_df)
    assert len(dataset) == 3
    assert {"conv_rate", "acc_rate", "avg_daily_trips", "label"} <= set(dataset.columns)
    assert dataset["conv_rate"].notna().all()
