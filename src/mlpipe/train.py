"""Train the model and write model.joblib + metrics.json + model_card.md."""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import train_test_split

from mlpipe import FEATURES, TARGET
from mlpipe.data import synthetic, validate
from mlpipe.evaluate import metrics


def train(df: pd.DataFrame, seed: int = 42, **params):
    X_train, X_test, y_train, y_test = train_test_split(
        df[FEATURES], df[TARGET], test_size=0.2, random_state=seed, stratify=df[TARGET]
    )
    model = HistGradientBoostingClassifier(
        max_iter=params.get("max_iter", 300),
        learning_rate=params.get("learning_rate", 0.05),
        max_leaf_nodes=params.get("max_leaf_nodes", 31),
        early_stopping=True,
        random_state=seed,
    ).fit(X_train, y_train)
    return model, metrics(model, X_test, y_test)


def git_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def model_card(result: dict, rows: int) -> str:
    lines = [
        "# Model card: credit-default",
        "",
        f"- Trained: {result['trained_at']}",
        f"- Commit: {result['git_sha']}",
        f"- Training rows: {rows}",
        f"- Features: {', '.join(FEATURES)}",
        "",
        "| Metric | Value |",
        "|---|---|",
        *[f"| {k} | {v:.4f} |" for k, v in result["metrics"].items()],
        "",
        "Intended use: ranking applications for manual review. Not for automated decisions without human oversight.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", help="CSV with features and target; omit to use synthetic data")
    parser.add_argument("--out", default="artifacts")
    args = parser.parse_args()

    df = pd.read_csv(args.data) if args.data else synthetic()
    report = validate(df)
    if not report.ok:
        raise SystemExit("data validation failed:\n  " + "\n  ".join(report.errors))

    model, scores = train(df)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    result = {"metrics": scores, "trained_at": datetime.now(UTC).isoformat(), "git_sha": git_sha()}
    joblib.dump(model, out / "model.joblib")
    (out / "metrics.json").write_text(json.dumps(result, indent=2))
    (out / "model_card.md").write_text(model_card(result, len(df)))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
