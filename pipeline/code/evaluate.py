"""SageMaker Processing: evaluate the trained model on the test split.

Writes /opt/ml/processing/evaluation/evaluation.json in the format that
SageMaker Model Registry expects for model quality metrics.
"""

from __future__ import annotations

import json
import os
import tarfile

import joblib
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score

BASE = "/opt/ml/processing"


def evaluate(model, test: pd.DataFrame) -> dict:
    X, y = test.drop(columns=["target"]), test["target"]
    predictions = model.predict(X)
    return {
        "metrics": {
            "accuracy": {"value": float(accuracy_score(y, predictions))},
            "f1_macro": {"value": float(f1_score(y, predictions, average="macro"))},
        }
    }


def main(base: str = BASE) -> None:
    with tarfile.open(os.path.join(base, "model", "model.tar.gz")) as tar:
        tar.extractall(path=os.path.join(base, "model"), filter="data")
    model = joblib.load(os.path.join(base, "model", "model.joblib"))
    test = pd.read_csv(os.path.join(base, "test", "test.csv"))

    report = evaluate(model, test)
    os.makedirs(os.path.join(base, "evaluation"), exist_ok=True)
    with open(os.path.join(base, "evaluation", "evaluation.json"), "w") as f:
        json.dump(report, f)
    print(json.dumps(report))


if __name__ == "__main__":
    main()
