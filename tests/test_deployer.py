import boto3
import handler
from botocore.stub import ANY, Stubber

PKG = "arn:aws:sagemaker:us-east-1:123456789012:model-package/churn-models/7"


def test_resource_names_include_version_and_fit_limits():
    model, config = handler.resource_names("churn", PKG, now=0)
    assert model == "churn-v7-19700101000000"
    assert config == "churn-v7-19700101000000-cfg"
    assert len(handler.resource_names("x" * 80, PKG)[1]) <= 63


def _stub_common(stub):
    stub.add_response(
        "create_model",
        {"ModelArn": "arn:aws:sagemaker:us-east-1:123456789012:model/m"},
        {
            "ModelName": ANY,
            "ExecutionRoleArn": "arn:aws:iam::123456789012:role/sm",
            "Containers": [{"ModelPackageName": PKG}],
        },
    )
    stub.add_response(
        "create_endpoint_config",
        {"EndpointConfigArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint-config/c"},
        {
            "EndpointConfigName": ANY,
            "ProductionVariants": ANY,
        },
    )


def test_creates_endpoint_when_missing():
    sm = boto3.client("sagemaker", region_name="us-east-1")
    with Stubber(sm) as stub:
        _stub_common(stub)
        stub.add_client_error(
            "describe_endpoint",
            service_error_code="ValidationException",
            service_message='Could not find endpoint "churn".',
        )
        stub.add_response(
            "create_endpoint",
            {"EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/churn"},
            {"EndpointName": "churn", "EndpointConfigName": ANY},
        )
        result = handler.deploy(sm, PKG, "churn", "arn:aws:iam::123456789012:role/sm", "ml.m5.large", 1)
    assert result["action"] == "created"


def test_updates_existing_endpoint():
    sm = boto3.client("sagemaker", region_name="us-east-1")
    with Stubber(sm) as stub:
        _stub_common(stub)
        stub.add_response(
            "describe_endpoint",
            {
                "EndpointName": "churn",
                "EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/churn",
                "EndpointConfigName": "old",
                "EndpointStatus": "InService",
                "CreationTime": "2026-01-01T00:00:00Z",
                "LastModifiedTime": "2026-01-01T00:00:00Z",
            },
            {"EndpointName": "churn"},
        )
        stub.add_response(
            "update_endpoint",
            {"EndpointArn": "arn:aws:sagemaker:us-east-1:123456789012:endpoint/churn"},
            {"EndpointName": "churn", "EndpointConfigName": ANY},
        )
        result = handler.deploy(sm, PKG, "churn", "arn:aws:iam::123456789012:role/sm", "ml.m5.large", 1)
    assert result["action"] == "updated"


def test_handler_ignores_non_approved_events():
    assert handler.handler({"detail": {"ModelApprovalStatus": "Rejected"}}, None) == {"skipped": "Rejected"}
