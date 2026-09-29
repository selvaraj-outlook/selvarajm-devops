import io

import boto3
import numpy as np
import pandas as pd
from moto import mock_aws

from drift import job


def _put(s3, key, df):
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    s3.put_object(Bucket="data", Key=key, Body=buf.getvalue())


@mock_aws
def test_job_reads_s3_and_pushes_metrics():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="data")
    rng = np.random.default_rng(1)
    _put(s3, "reference/train.parquet", pd.DataFrame({"x": rng.normal(0, 1, 2000), "y": rng.normal(5, 1, 2000)}))
    _put(
        s3,
        "inference/date=2026-09-29/part-0.parquet",
        pd.DataFrame({"x": rng.normal(2, 1, 500), "y": rng.normal(5, 1, 500)}),
    )
    _put(
        s3,
        "inference/date=2026-09-29/part-1.parquet",
        pd.DataFrame({"x": rng.normal(2, 1, 500), "y": rng.normal(5, 1, 500)}),
    )

    pushed = {}

    def fake_push(url, job, grouping_key, registry):
        pushed.update(url=url, job=job, key=grouping_key, registry=registry)

    env = {
        "DATA_BUCKET": "data",
        "CURRENT_PREFIX": "inference/date=2026-09-29/",
        "MODEL_NAME": "fraud",
        "PUSHGATEWAY_URL": "http://pushgateway:9091",
    }
    report = job.run(env, s3=s3, push=fake_push)

    assert report.current_rows == 1000
    assert pushed["key"] == {"model": "fraud"}
    registry = pushed["registry"]
    assert (
        registry.get_sample_value("model_feature_drifted", {"model": "fraud", "feature": "x", "kind": "numeric"}) == 1
    )
    assert (
        registry.get_sample_value("model_feature_drifted", {"model": "fraud", "feature": "y", "kind": "numeric"}) == 0
    )
    assert registry.get_sample_value("model_drift_share", {"model": "fraud"}) == 0.5


@mock_aws
def test_missing_window_raises():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="data")
    try:
        job.read_parquet(s3, "data", "inference/date=1999-01-01/")
    except FileNotFoundError as err:
        assert "no parquet files" in str(err)
    else:
        raise AssertionError("expected FileNotFoundError")
