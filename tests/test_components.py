import json
import sys

import make_data
import mlflow
import pandas as pd

import prep
import register
import train


def test_prep_train_register_gate(tmp_path, monkeypatch):
    raw = tmp_path / "raw"
    raw.mkdir()
    make_data.build().to_csv(raw / "data.csv", index=False)

    monkeypatch.setattr(
        sys,
        "argv",
        ["prep.py", "--raw_data", str(raw), "--train_data", str(tmp_path / "tr"), "--test_data", str(tmp_path / "te")],
    )
    prep.main()
    train_df = pd.read_csv(tmp_path / "tr" / "data.csv")
    test_df = pd.read_csv(tmp_path / "te" / "data.csv")
    assert len(train_df) > len(test_df) > 0

    mlflow.set_tracking_uri(f"file://{tmp_path}/mlruns")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train.py",
            "--train_data",
            str(tmp_path / "tr"),
            "--test_data",
            str(tmp_path / "te"),
            "--n_estimators",
            "100",
            "--model_output",
            str(tmp_path / "model"),
            "--metrics_output",
            str(tmp_path / "m"),
        ],
    )
    train.main()
    metrics = json.loads((tmp_path / "m" / "metrics.json").read_text())
    assert metrics["roc_auc"] >= 0.95, metrics  # the default gate in aml/pipeline.yaml
    assert (tmp_path / "model" / "MLmodel").exists()


def test_gate():
    assert register.passes_gate({"roc_auc": 0.97}, 0.95)[0]
    ok, reason = register.passes_gate({"roc_auc": 0.90}, 0.95)
    assert not ok and "0.9000 < 0.95" in reason
