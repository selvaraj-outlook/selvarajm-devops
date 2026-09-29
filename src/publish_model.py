"""Train the wine classifier and publish it as an immutable model version in S3.

    python src/publish_model.py --bucket <model_bucket> --version v2 --n-estimators 200

The KServe sklearn runtime loads `model.joblib` from the version prefix.
Versions are immutable: publishing to an existing prefix fails.
"""

from __future__ import annotations

import argparse
import io
import json

import boto3
import joblib
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

MODEL_NAME = "wine-classifier"


class VersionExistsError(RuntimeError):
    pass


def train(n_estimators: int, seed: int = 42) -> tuple[RandomForestClassifier, float]:
    X, y = load_wine(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)
    model = RandomForestClassifier(n_estimators=n_estimators, random_state=seed).fit(X_train, y_train)
    return model, accuracy_score(y_test, model.predict(X_test))


def publish(model, accuracy: float, bucket: str, version: str, s3=None) -> str:
    s3 = s3 or boto3.client("s3")
    prefix = f"{MODEL_NAME}/{version}/"
    if s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=1).get("KeyCount", 0):
        raise VersionExistsError(f"s3://{bucket}/{prefix} already exists; versions are immutable")

    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    s3.put_object(Bucket=bucket, Key=prefix + "model.joblib", Body=buffer.getvalue())
    s3.put_object(
        Bucket=bucket,
        Key=prefix + "metadata.json",
        Body=json.dumps({"model": MODEL_NAME, "version": version, "accuracy": accuracy}).encode(),
        ContentType="application/json",
    )
    return f"s3://{bucket}/{prefix}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--version", required=True, help="e.g. v1, v2")
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--min-accuracy", type=float, default=0.85)
    args = parser.parse_args()

    model, accuracy = train(args.n_estimators)
    if accuracy < args.min_accuracy:
        raise SystemExit(f"accuracy {accuracy:.3f} below gate {args.min_accuracy}; not publishing")
    print(publish(model, accuracy, args.bucket, args.version), f"accuracy={accuracy:.3f}")


if __name__ == "__main__":
    main()
