"""Deploy an approved model package to a SageMaker real-time endpoint.

Triggered by EventBridge on "SageMaker Model Package State Change" when a
package in the watched group becomes Approved. Creates a new model and
endpoint config, then creates the endpoint or updates it in place (SageMaker
performs a blue/green swap, so the endpoint stays available).
"""

from __future__ import annotations

import os
import time

import boto3

sm = boto3.client("sagemaker")


def resource_names(prefix: str, package_arn: str, now: float | None = None) -> tuple[str, str]:
    version = package_arn.rsplit("/", 1)[-1]
    stamp = time.strftime("%Y%m%d%H%M%S", time.gmtime(now))
    base = f"{prefix}-v{version}-{stamp}"[:63]
    return base, f"{base}-cfg"[:63]


def endpoint_exists(client, name: str) -> bool:
    try:
        client.describe_endpoint(EndpointName=name)
        return True
    except client.exceptions.ClientError as err:
        if "Could not find endpoint" in str(err):
            return False
        raise


def deploy(client, package_arn: str, endpoint: str, role_arn: str, instance_type: str, count: int) -> dict:
    model_name, config_name = resource_names(endpoint, package_arn)
    client.create_model(
        ModelName=model_name,
        ExecutionRoleArn=role_arn,
        Containers=[{"ModelPackageName": package_arn}],
    )
    client.create_endpoint_config(
        EndpointConfigName=config_name,
        ProductionVariants=[
            {
                "VariantName": "AllTraffic",
                "ModelName": model_name,
                "InstanceType": instance_type,
                "InitialInstanceCount": count,
            }
        ],
    )
    if endpoint_exists(client, endpoint):
        client.update_endpoint(EndpointName=endpoint, EndpointConfigName=config_name)
        action = "updated"
    else:
        client.create_endpoint(EndpointName=endpoint, EndpointConfigName=config_name)
        action = "created"
    return {"endpoint": endpoint, "action": action, "model": model_name, "config": config_name}


def handler(event, _context):
    detail = event["detail"]
    if detail.get("ModelApprovalStatus") != "Approved":
        return {"skipped": detail.get("ModelApprovalStatus")}
    return deploy(
        sm,
        package_arn=detail["ModelPackageArn"],
        endpoint=os.environ["ENDPOINT_NAME"],
        role_arn=os.environ["EXECUTION_ROLE_ARN"],
        instance_type=os.environ.get("INSTANCE_TYPE", "ml.m5.large"),
        count=int(os.environ.get("INSTANCE_COUNT", "1")),
    )
