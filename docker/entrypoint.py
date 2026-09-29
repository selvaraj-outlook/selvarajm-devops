"""Start the MLflow tracking server.

The database password is never stored in Kubernetes. At start-up this script
reads the RDS-managed secret from AWS Secrets Manager (via IRSA), builds the
backend-store URI and execs `mlflow server`.

Required environment variables:
  DB_SECRET_ARN      Secrets Manager ARN of the RDS master user secret
  DB_HOST            RDS endpoint host (without port)
  ARTIFACT_BUCKET    S3 bucket for artifacts
Optional:
  DB_PORT (5432), DB_NAME (mlflow), ARTIFACT_PREFIX (artifacts), WORKERS (2)
"""

from __future__ import annotations

import json
import os
import sys
from urllib.parse import quote_plus


def build_backend_uri(secret: dict, host: str, port: str, db_name: str) -> str:
    """Return a SQLAlchemy URI for PostgreSQL with URL-escaped credentials."""
    user = quote_plus(secret["username"])
    password = quote_plus(secret["password"])
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}?sslmode=require"


def fetch_secret(secret_arn: str, client=None) -> dict:
    if client is None:
        import boto3

        client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def build_command(env: dict, secret: dict) -> list[str]:
    backend = build_backend_uri(
        secret,
        host=env["DB_HOST"],
        port=env.get("DB_PORT", "5432"),
        db_name=env.get("DB_NAME", "mlflow"),
    )
    artifacts = f"s3://{env['ARTIFACT_BUCKET']}/{env.get('ARTIFACT_PREFIX', 'artifacts')}"
    return [
        "mlflow",
        "server",
        "--host", "0.0.0.0",
        "--port", "5000",
        "--workers", env.get("WORKERS", "2"),
        "--backend-store-uri", backend,
        "--artifacts-destination", artifacts,
        "--serve-artifacts",
    ]


def main() -> None:
    missing = [k for k in ("DB_SECRET_ARN", "DB_HOST", "ARTIFACT_BUCKET") if not os.environ.get(k)]
    if missing:
        sys.exit(f"missing required environment variables: {', '.join(missing)}")
    secret = fetch_secret(os.environ["DB_SECRET_ARN"])
    command = build_command(dict(os.environ), secret)
    os.execvp(command[0], command)


if __name__ == "__main__":
    main()
