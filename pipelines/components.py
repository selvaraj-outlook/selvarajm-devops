"""Lightweight KFP v2 Python components.

Each component runs in its own container (base image + packages_to_install),
so the function bodies import what they need locally.
"""

from kfp import dsl
from kfp.dsl import Dataset, Input, Metrics, Model, Output

BASE_IMAGE = "python:3.11-slim"
SKLEARN = ["pandas==2.2.3", "scikit-learn==1.5.2"]


@dsl.component(base_image=BASE_IMAGE, packages_to_install=SKLEARN)
def load_data(test_size: float, seed: int, train_data: Output[Dataset], test_data: Output[Dataset]):
    """Load the breast-cancer dataset and write a stratified train/test split."""
    from sklearn.datasets import load_breast_cancer
    from sklearn.model_selection import train_test_split

    X, y = load_breast_cancer(return_X_y=True, as_frame=True)
    df = X.assign(target=y)
    train, test = train_test_split(df, test_size=test_size, random_state=seed, stratify=df["target"])
    train.to_csv(train_data.path, index=False)
    test.to_csv(test_data.path, index=False)
    train_data.metadata["rows"] = len(train)
    test_data.metadata["rows"] = len(test)


@dsl.component(base_image=BASE_IMAGE, packages_to_install=[*SKLEARN, "joblib==1.4.2"])
def train_model(
    train_data: Input[Dataset],
    n_estimators: int,
    max_depth: int,
    model: Output[Model],
):
    """Train a random forest and save it with joblib."""
    import joblib
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier

    df = pd.read_csv(train_data.path)
    clf = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth or None, random_state=42)
    clf.fit(df.drop(columns=["target"]), df["target"])
    joblib.dump(clf, model.path)
    model.metadata.update({"framework": "scikit-learn", "n_estimators": n_estimators, "max_depth": max_depth})


@dsl.component(base_image=BASE_IMAGE, packages_to_install=[*SKLEARN, "joblib==1.4.2"])
def evaluate_model(test_data: Input[Dataset], model: Input[Model], metrics: Output[Metrics]) -> float:
    """Evaluate on the held-out set; returns accuracy for the quality gate."""
    import joblib
    import pandas as pd
    from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

    df = pd.read_csv(test_data.path)
    X, y = df.drop(columns=["target"]), df["target"]
    clf = joblib.load(model.path)
    predictions = clf.predict(X)
    accuracy = float(accuracy_score(y, predictions))
    metrics.log_metric("accuracy", accuracy)
    metrics.log_metric("f1", float(f1_score(y, predictions)))
    metrics.log_metric("roc_auc", float(roc_auc_score(y, clf.predict_proba(X)[:, 1])))
    return accuracy


@dsl.component(base_image=BASE_IMAGE, packages_to_install=["boto3==1.35.54"])
def publish_model(model: Input[Model], bucket: str, model_name: str, accuracy: float) -> str:
    """Copy the approved model to S3 under a timestamped version prefix (uses IRSA)."""
    import json
    import time

    import boto3

    version = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
    prefix = f"{model_name}/{version}"
    s3 = boto3.client("s3")
    s3.upload_file(model.path, bucket, f"{prefix}/model.joblib")
    s3.put_object(
        Bucket=bucket,
        Key=f"{prefix}/metadata.json",
        Body=json.dumps({"model": model_name, "version": version, "accuracy": accuracy}).encode(),
    )
    return f"s3://{bucket}/{prefix}/"
