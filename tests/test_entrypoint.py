import json
import sys
from pathlib import Path

import boto3
from moto import mock_aws

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "docker"))
import entrypoint  # noqa: E402


def test_backend_uri_escapes_special_characters():
    uri = entrypoint.build_backend_uri({"username": "mlflow", "password": "p@ss:w/rd"}, "db.local", "5432", "mlflow")
    assert uri == "postgresql+psycopg2://mlflow:p%40ss%3Aw%2Frd@db.local:5432/mlflow?sslmode=require"


def test_build_command_uses_s3_artifacts_and_defaults():
    env = {"DB_HOST": "db.local", "ARTIFACT_BUCKET": "bucket"}
    cmd = entrypoint.build_command(env, {"username": "u", "password": "p"})
    assert cmd[:2] == ["mlflow", "server"]
    assert cmd[cmd.index("--artifacts-destination") + 1] == "s3://bucket/artifacts"
    assert "--serve-artifacts" in cmd
    assert cmd[cmd.index("--workers") + 1] == "2"


@mock_aws
def test_fetch_secret_reads_secrets_manager():
    client = boto3.client("secretsmanager", region_name="us-east-1")
    arn = client.create_secret(Name="rds-secret", SecretString=json.dumps({"username": "u", "password": "p"}))["ARN"]
    assert entrypoint.fetch_secret(arn, client=client) == {"username": "u", "password": "p"}
