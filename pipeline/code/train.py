"""SageMaker Training (scikit-learn script mode).

Reads SM_CHANNEL_TRAIN/train.csv and writes model.joblib to SM_MODEL_DIR.
"""

from __future__ import annotations

import argparse
import os

import joblib
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier


def fit(train: pd.DataFrame, n_estimators: int, learning_rate: float, max_depth: int) -> GradientBoostingClassifier:
    X, y = train.drop(columns=["target"]), train["target"]
    model = GradientBoostingClassifier(
        n_estimators=n_estimators, learning_rate=learning_rate, max_depth=max_depth, random_state=42
    )
    return model.fit(X, y)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_estimators", type=int, default=150)
    parser.add_argument("--learning_rate", type=float, default=0.1)
    parser.add_argument("--max_depth", type=int, default=3)
    parser.add_argument("--train", default=os.environ.get("SM_CHANNEL_TRAIN", "/opt/ml/input/data/train"))
    parser.add_argument("--model-dir", default=os.environ.get("SM_MODEL_DIR", "/opt/ml/model"))
    args, _ = parser.parse_known_args()

    train = pd.read_csv(os.path.join(args.train, "train.csv"))
    model = fit(train, args.n_estimators, args.learning_rate, args.max_depth)
    joblib.dump(model, os.path.join(args.model_dir, "model.joblib"))


if __name__ == "__main__":
    main()
