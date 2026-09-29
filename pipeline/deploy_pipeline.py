"""Package the pipeline code, upload it to S3 and create or update the pipeline.

    python -m pipeline.deploy_pipeline --name churn-pipeline --bucket <bucket> \
        --role-arn <sagemaker_execution_role_arn> --model-package-group <group> [--start]

The values come from `terraform output`.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
from pathlib import Path

import boto3

from pipeline.definition import PipelineConfig, build_definition

CODE_DIR = Path(__file__).parent / "code"
# scikit-learn 1.2-1 framework image, us-east-1. See the README for other regions.
DEFAULT_IMAGE = "683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3"


def build_sourcedir(code_dir: Path = CODE_DIR) -> bytes:
    """Deterministic tar.gz of the training/inference scripts."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        for path in sorted(code_dir.glob("*.py")):
            info = tar.gettarinfo(str(path), arcname=path.name)
            info.mtime, info.uid, info.gid, info.uname, info.gname = 0, 0, 0, "", ""
            with path.open("rb") as f:
                tar.addfile(info, f)
    return buffer.getvalue()


def upload_code(s3, bucket: str, code_dir: Path = CODE_DIR) -> str:
    """Upload scripts under a content-addressed prefix and return that prefix."""
    sourcedir = build_sourcedir(code_dir)
    digest = hashlib.sha256(sourcedir).hexdigest()[:12]
    prefix = f"code/{digest}"
    s3.put_object(Bucket=bucket, Key=f"{prefix}/sourcedir.tar.gz", Body=sourcedir)
    for path in sorted(code_dir.glob("*.py")):
        s3.put_object(Bucket=bucket, Key=f"{prefix}/{path.name}", Body=path.read_bytes())
    return prefix


def upsert_pipeline(sm, name: str, role_arn: str, definition: dict) -> str:
    body = json.dumps(definition)
    try:
        response = sm.update_pipeline(PipelineName=name, PipelineDefinition=body, RoleArn=role_arn)
    except sm.exceptions.ResourceNotFound:
        response = sm.create_pipeline(
            PipelineName=name, PipelineDefinition=body, RoleArn=role_arn, PipelineDisplayName=name
        )
    return response["PipelineArn"]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--role-arn", required=True)
    parser.add_argument("--model-package-group", required=True)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--start", action="store_true", help="start an execution after deploying")
    args = parser.parse_args()

    s3, sm = boto3.client("s3"), boto3.client("sagemaker")
    prefix = upload_code(s3, args.bucket)
    cfg = PipelineConfig(
        role_arn=args.role_arn,
        bucket=args.bucket,
        code_prefix=prefix,
        model_package_group=args.model_package_group,
        sklearn_image=args.image,
    )
    arn = upsert_pipeline(sm, args.name, args.role_arn, build_definition(cfg))
    print(f"pipeline: {arn} (code s3://{args.bucket}/{prefix})")
    if args.start:
        execution = sm.start_pipeline_execution(PipelineName=args.name)
        print(f"execution: {execution['PipelineExecutionArn']}")


if __name__ == "__main__":
    main()
