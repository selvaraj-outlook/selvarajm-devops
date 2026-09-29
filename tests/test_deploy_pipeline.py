import json

import boto3
from botocore.stub import ANY, Stubber
from moto import mock_aws

from pipeline import deploy_pipeline


def test_sourcedir_is_deterministic():
    assert deploy_pipeline.build_sourcedir() == deploy_pipeline.build_sourcedir()


@mock_aws
def test_upload_code_uses_content_addressed_prefix():
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="bucket")
    prefix = deploy_pipeline.upload_code(s3, "bucket")
    keys = {o["Key"] for o in s3.list_objects_v2(Bucket="bucket")["Contents"]}
    assert f"{prefix}/sourcedir.tar.gz" in keys
    assert f"{prefix}/train.py" in keys
    assert deploy_pipeline.upload_code(s3, "bucket") == prefix


def test_upsert_creates_when_pipeline_missing():
    sm = boto3.client("sagemaker", region_name="us-east-1")
    arn = "arn:aws:sagemaker:us-east-1:123456789012:pipeline/churn"
    with Stubber(sm) as stub:
        stub.add_client_error("update_pipeline", service_error_code="ResourceNotFound")
        stub.add_response(
            "create_pipeline",
            {"PipelineArn": arn},
            {
                "PipelineName": "churn",
                "PipelineDefinition": ANY,
                "RoleArn": "arn:aws:iam::123456789012:role/sm",
                "PipelineDisplayName": "churn",
            },
        )
        assert (
            deploy_pipeline.upsert_pipeline(sm, "churn", "arn:aws:iam::123456789012:role/sm", {"Version": "2020-12-01"})
            == arn
        )


def test_upsert_updates_existing_pipeline():
    sm = boto3.client("sagemaker", region_name="us-east-1")
    arn = "arn:aws:sagemaker:us-east-1:123456789012:pipeline/churn"
    with Stubber(sm) as stub:
        stub.add_response(
            "update_pipeline",
            {"PipelineArn": arn},
            {
                "PipelineName": "churn",
                "PipelineDefinition": json.dumps({"a": 1}),
                "RoleArn": "arn:aws:iam::123456789012:role/sm",
            },
        )
        assert deploy_pipeline.upsert_pipeline(sm, "churn", "arn:aws:iam::123456789012:role/sm", {"a": 1}) == arn
