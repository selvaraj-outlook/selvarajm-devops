import sys
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import publish_model  # noqa: E402


@pytest.fixture
def s3():
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="models")
        yield client


def test_train_meets_quality_gate():
    _, accuracy = publish_model.train(n_estimators=20)
    assert accuracy > 0.85


def test_publish_writes_model_and_metadata(s3):
    model, accuracy = publish_model.train(n_estimators=10)
    uri = publish_model.publish(model, accuracy, "models", "v1", s3=s3)
    assert uri == "s3://models/wine-classifier/v1/"
    keys = {o["Key"] for o in s3.list_objects_v2(Bucket="models")["Contents"]}
    assert keys == {"wine-classifier/v1/model.joblib", "wine-classifier/v1/metadata.json"}


def test_versions_are_immutable(s3):
    model, accuracy = publish_model.train(n_estimators=10)
    publish_model.publish(model, accuracy, "models", "v1", s3=s3)
    with pytest.raises(publish_model.VersionExistsError):
        publish_model.publish(model, accuracy, "models", "v1", s3=s3)
