import sys
from pathlib import Path

import mlflow

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
import train  # noqa: E402


def test_train_logs_run_and_registers_model(tmp_path):
    mlflow.set_tracking_uri(f"sqlite:///{tmp_path}/mlflow.db")
    mlflow.set_registry_uri(f"sqlite:///{tmp_path}/mlflow.db")
    import os

    os.environ["MLFLOW_ARTIFACT_ROOT"] = str(tmp_path / "artifacts")
    result = train.train(n_estimators=20, max_depth=4)

    assert result["accuracy"] > 0.85
    run = mlflow.get_run(result["run_id"])
    assert run.data.params["n_estimators"] == "20"
    versions = mlflow.MlflowClient().search_model_versions(f"name='{train.MODEL_NAME}'")
    assert len(versions) == 1
