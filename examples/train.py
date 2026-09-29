"""Train a model, log it to MLflow and register it.

    export MLFLOW_TRACKING_URI=http://localhost:5000   # kubectl port-forward
    python examples/train.py --n-estimators 200 --max-depth 6
"""

from __future__ import annotations

import argparse

import mlflow
import mlflow.sklearn
from mlflow.models import infer_signature
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split

EXPERIMENT = "wine-quality"
MODEL_NAME = "wine-classifier"


def train(n_estimators: int, max_depth: int | None, seed: int = 42, register: bool = True) -> dict:
    X, y = load_wine(return_X_y=True, as_frame=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=seed, stratify=y)

    mlflow.set_experiment(EXPERIMENT)
    with mlflow.start_run() as run:
        params = {"n_estimators": n_estimators, "max_depth": max_depth, "seed": seed}
        mlflow.log_params(params)

        model = RandomForestClassifier(n_estimators=n_estimators, max_depth=max_depth, random_state=seed)
        model.fit(X_train, y_train)
        predictions = model.predict(X_test)

        metrics = {
            "accuracy": accuracy_score(y_test, predictions),
            "f1_macro": f1_score(y_test, predictions, average="macro"),
        }
        mlflow.log_metrics(metrics)

        mlflow.sklearn.log_model(
            model,
            artifact_path="model",
            signature=infer_signature(X_test, predictions),
            input_example=X_test.head(3),
            registered_model_name=MODEL_NAME if register else None,
        )
        return {"run_id": run.info.run_id, **metrics}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-estimators", type=int, default=100)
    parser.add_argument("--max-depth", type=int, default=None)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    result = train(args.n_estimators, args.max_depth, args.seed)
    print(result)


if __name__ == "__main__":
    main()
