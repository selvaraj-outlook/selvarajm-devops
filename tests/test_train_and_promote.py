import json

import boto3
from moto import mock_aws

from mlpipe import registry
from mlpipe.data import synthetic
from mlpipe.evaluate import should_promote
from mlpipe.train import model_card, train


def test_model_clears_quality_bar():
    _, scores = train(synthetic(4000))
    assert scores["roc_auc"] > 0.75
    assert 0 < scores["brier"] < 0.25


def test_promotion_rules():
    good = {"roc_auc": 0.82, "brier": 0.10}
    assert should_promote(good, None)[0]
    assert not should_promote({"roc_auc": 0.60, "brier": 0.1}, None)[0]
    assert not should_promote({"roc_auc": 0.80, "brier": 0.10}, good)[0]  # AUC regression
    assert should_promote({"roc_auc": 0.818, "brier": 0.10}, good)[0]  # within tolerance
    assert not should_promote({"roc_auc": 0.83, "brier": 0.12}, good)[0]  # worse calibration


def test_model_card_lists_metrics():
    card = model_card({"metrics": {"roc_auc": 0.8}, "trained_at": "t", "git_sha": "abc"}, 100)
    assert "| roc_auc | 0.8000 |" in card


@mock_aws
def test_registry_champion_roundtrip(tmp_path):
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="models")
    assert registry.get_champion(s3, "models") is None
    for name in registry.ARTIFACTS:
        (tmp_path / name).write_text("x")
    assert registry.upload(s3, "models", "v1", tmp_path) == "s3://models/models/v1/"
    registry.promote(s3, "models", "v1", {"roc_auc": 0.8})
    assert registry.get_champion(s3, "models") == {"version": "v1", "metrics": {"roc_auc": 0.8}}
    assert json.loads(s3.get_object(Bucket="models", Key="champion.json")["Body"].read())["version"] == "v1"
