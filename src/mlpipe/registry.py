"""A minimal S3 model registry with a champion pointer.

s3://<bucket>/models/<version>/{model.joblib,metrics.json,model_card.md}
s3://<bucket>/champion.json  -> {"version": "...", "metrics": {...}}
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3

from mlpipe.evaluate import should_promote

ARTIFACTS = ("model.joblib", "metrics.json", "model_card.md")


def get_champion(s3, bucket: str) -> dict | None:
    try:
        return json.loads(s3.get_object(Bucket=bucket, Key="champion.json")["Body"].read())
    except s3.exceptions.NoSuchKey:
        return None


def upload(s3, bucket: str, version: str, artifacts: Path) -> str:
    for name in ARTIFACTS:
        s3.upload_file(str(artifacts / name), bucket, f"models/{version}/{name}")
    return f"s3://{bucket}/models/{version}/"


def promote(s3, bucket: str, version: str, metrics: dict) -> None:
    s3.put_object(
        Bucket=bucket,
        Key="champion.json",
        Body=json.dumps({"version": version, "metrics": metrics}).encode(),
        ContentType="application/json",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Upload a candidate and decide whether it becomes champion.")
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--version", required=True)
    parser.add_argument("--artifacts", default="artifacts")
    parser.add_argument("--promote", action="store_true", help="update champion.json if the gate passes")
    parser.add_argument("--github-output", help="path of $GITHUB_OUTPUT to write the decision to")
    args = parser.parse_args()

    s3 = boto3.client("s3")
    artifacts = Path(args.artifacts)
    challenger = json.loads((artifacts / "metrics.json").read_text())["metrics"]
    champion = get_champion(s3, args.bucket)
    ok, reason = should_promote(challenger, champion["metrics"] if champion else None)
    print(f"promote={ok}: {reason}")

    print(upload(s3, args.bucket, args.version, artifacts))
    if ok and args.promote:
        promote(s3, args.bucket, args.version, challenger)
    if args.github_output:
        with open(args.github_output, "a") as f:
            f.write(f"promote={'true' if ok else 'false'}\nreason={reason}\n")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
