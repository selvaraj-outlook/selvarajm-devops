"""Build a point-in-time-correct training dataset from the offline store.

Each label row is joined with the feature values that were known at its
timestamp, which prevents leakage from the future.
"""

from __future__ import annotations

import argparse

import pandas as pd
from feast import FeatureStore


def build(store: FeatureStore, entity_df: pd.DataFrame) -> pd.DataFrame:
    service = store.get_feature_service("driver_activity_v1")
    return store.get_historical_features(entity_df=entity_df, features=service).to_df()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="feature_repo")
    parser.add_argument("--labels", required=True, help="parquet with driver_id, event_timestamp, label")
    parser.add_argument("--out", default="data/training.parquet")
    args = parser.parse_args()
    dataset = build(FeatureStore(repo_path=args.repo), pd.read_parquet(args.labels))
    dataset.to_parquet(args.out, index=False)
    print(f"{len(dataset)} rows -> {args.out}")


if __name__ == "__main__":
    main()
