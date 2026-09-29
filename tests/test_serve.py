import json

import joblib
import pytest
from fastapi.testclient import TestClient

from mlpipe.data import synthetic
from mlpipe.train import train

APPLICANT = {"income": 52000, "debt_ratio": 0.4, "age": 35, "open_credit_lines": 5, "late_payments_90d": 0}


@pytest.fixture(scope="module")
def client(tmp_path_factory):
    model_dir = tmp_path_factory.mktemp("model")
    model, scores = train(synthetic(2000))
    joblib.dump(model, model_dir / "model.joblib")
    (model_dir / "metrics.json").write_text(json.dumps({"metrics": scores}))

    import mlpipe.serve as serve

    serve.MODEL_DIR = model_dir
    serve.model.cache_clear()
    return TestClient(serve.app)


def test_health(client):
    assert client.get("/health").json()["status"] == "ok"


def test_predict_returns_probability(client):
    risky = {**APPLICANT, "debt_ratio": 3.5, "late_payments_90d": 4}
    body = client.post("/predict", json=[APPLICANT, risky]).json()
    assert len(body) == 2
    assert 0 <= body[0]["default_probability"] < body[1]["default_probability"] <= 1


def test_invalid_input_rejected(client):
    assert client.post("/predict", json=[{**APPLICANT, "age": 12}]).status_code == 422
