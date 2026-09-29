"""Drift-monitoring job: compare the latest inference window with the
training reference and push the results to a Prometheus Pushgateway.

Environment:
  DATA_BUCKET        S3 bucket with reference/ and inference/ data
  REFERENCE_KEY      e.g. reference/train.parquet
  CURRENT_PREFIX     e.g. inference/date=2026-09-29/   (default: today's partition)
  MODEL_NAME         label on every metric
  PUSHGATEWAY_URL    e.g. http://prometheus-pushgateway.monitoring:9091
  FEATURES           optional comma-separated list of columns to check
"""

from __future__ import annotations

import io
import json
import os
from datetime import UTC, datetime

import boto3
import pandas as pd
from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

from drift.detector import DriftReport, detect


def read_parquet(s3, bucket: str, key_or_prefix: str) -> pd.DataFrame:
    if key_or_prefix.endswith(".parquet"):
        keys = [key_or_prefix]
    else:
        pages = s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=key_or_prefix)
        keys = [o["Key"] for page in pages for o in page.get("Contents", []) if o["Key"].endswith(".parquet")]
    if not keys:
        raise FileNotFoundError(f"no parquet files at s3://{bucket}/{key_or_prefix}")
    frames = [pd.read_parquet(io.BytesIO(s3.get_object(Bucket=bucket, Key=k)["Body"].read())) for k in keys]
    return pd.concat(frames, ignore_index=True)


def build_registry(report: DriftReport, model: str) -> CollectorRegistry:
    registry = CollectorRegistry()
    labels = ["model", "feature", "kind"]
    psi = Gauge("model_feature_psi", "Population Stability Index per feature", labels, registry=registry)
    p_value = Gauge("model_feature_drift_p_value", "KS / chi-square p-value per feature", labels, registry=registry)
    drifted = Gauge("model_feature_drifted", "1 if the feature drifted", labels, registry=registry)
    for f in report.features:
        psi.labels(model, f.feature, f.kind).set(f.psi)
        p_value.labels(model, f.feature, f.kind).set(f.p_value)
        drifted.labels(model, f.feature, f.kind).set(int(f.drifted))
    Gauge("model_drift_share", "Share of drifted features", ["model"], registry=registry).labels(model).set(
        report.drift_share
    )
    Gauge("model_drift_current_rows", "Rows in the current window", ["model"], registry=registry).labels(model).set(
        report.current_rows
    )
    Gauge("model_drift_last_run_timestamp_seconds", "Last successful run", ["model"], registry=registry).labels(
        model
    ).set_to_current_time()
    return registry


def run(env: dict, s3=None, push=push_to_gateway) -> DriftReport:
    s3 = s3 or boto3.client("s3")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    bucket = env["DATA_BUCKET"]
    reference = read_parquet(s3, bucket, env.get("REFERENCE_KEY", "reference/train.parquet"))
    current = read_parquet(s3, bucket, env.get("CURRENT_PREFIX", f"inference/date={today}/"))
    features = [f for f in env.get("FEATURES", "").split(",") if f] or None

    report = detect(reference, current, features)
    model = env.get("MODEL_NAME", "model")
    push(
        env["PUSHGATEWAY_URL"], job="model-drift", grouping_key={"model": model}, registry=build_registry(report, model)
    )
    return report


def main() -> None:
    report = run(dict(os.environ))
    print(json.dumps(report.to_dict(), indent=2))


if __name__ == "__main__":
    main()
