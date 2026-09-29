"""Train a classifier, log metrics with MLflow and save an MLflow model.

In Azure ML the MLflow tracking URI is set automatically, so metrics and the
model show up on the job in the studio.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mlflow
import mlflow.sklearn
import pandas as pd
from mlflow.models import infer_signature
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

TARGET = "target"


def fit_and_score(train: pd.DataFrame, test: pd.DataFrame, n_estimators: int, max_depth: int):
    X_train, y_train = train.drop(columns=[TARGET]), train[TARGET]
    X_test, y_test = test.drop(columns=[TARGET]), test[TARGET]
    model = RandomForestClassifier(
        n_estimators=n_estimators, max_depth=max_depth or None, random_state=42, n_jobs=-1
    ).fit(X_train, y_train)
    proba = model.predict_proba(X_test)[:, 1]
    predictions = (proba >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_test, predictions)),
        "f1": float(f1_score(y_test, predictions)),
        "roc_auc": float(roc_auc_score(y_test, proba)),
    }
    return model, metrics, infer_signature(X_test, predictions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_data", required=True)
    parser.add_argument("--test_data", required=True)
    parser.add_argument("--n_estimators", type=int, default=200)
    parser.add_argument("--max_depth", type=int, default=10)
    parser.add_argument("--model_output", required=True)
    parser.add_argument("--metrics_output", required=True)
    args = parser.parse_args()

    train = pd.read_csv(Path(args.train_data) / "data.csv")
    test = pd.read_csv(Path(args.test_data) / "data.csv")

    with mlflow.start_run():
        mlflow.log_params({"n_estimators": args.n_estimators, "max_depth": args.max_depth})
        model, metrics, signature = fit_and_score(train, test, args.n_estimators, args.max_depth)
        mlflow.log_metrics(metrics)

    mlflow.sklearn.save_model(model, args.model_output, signature=signature)
    Path(args.metrics_output).mkdir(parents=True, exist_ok=True)
    (Path(args.metrics_output) / "metrics.json").write_text(json.dumps(metrics))
    print(json.dumps(metrics))


if __name__ == "__main__":
    main()
