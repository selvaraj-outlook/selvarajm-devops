"""Register the model in the workspace registry only if it clears the gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import mlflow


def passes_gate(metrics: dict, min_auc: float) -> tuple[bool, str]:
    auc = metrics.get("roc_auc", 0.0)
    if auc < min_auc:
        return False, f"roc_auc {auc:.4f} < {min_auc}"
    return True, f"roc_auc {auc:.4f} >= {min_auc}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", required=True)
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--model_name", default="breast-cancer-rf")
    parser.add_argument("--min_auc", type=float, default=0.95)
    args = parser.parse_args()

    metrics = json.loads((Path(args.metrics) / "metrics.json").read_text())
    ok, reason = passes_gate(metrics, args.min_auc)
    print(reason)
    if not ok:
        raise SystemExit(f"quality gate failed: {reason}")

    with mlflow.start_run():
        mlflow.log_metrics({f"gate_{k}": v for k, v in metrics.items()})
        model_info = mlflow.sklearn.log_model(mlflow.sklearn.load_model(args.model_path), artifact_path="model")
    version = mlflow.register_model(model_info.model_uri, args.model_name)
    print(f"registered {args.model_name}:{version.version}")


if __name__ == "__main__":
    main()
