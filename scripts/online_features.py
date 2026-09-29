"""Fetch the latest features for a driver from the online store (DynamoDB)."""

from __future__ import annotations

import argparse
import json

from feast import FeatureStore


def fetch(store: FeatureStore, driver_ids: list[int]) -> dict:
    return store.get_online_features(
        features=store.get_feature_service("driver_activity_v1"),
        entity_rows=[{"driver_id": d} for d in driver_ids],
    ).to_dict()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default="feature_repo")
    parser.add_argument("driver_ids", nargs="+", type=int)
    args = parser.parse_args()
    print(json.dumps(fetch(FeatureStore(repo_path=args.repo), args.driver_ids), indent=2, default=str))


if __name__ == "__main__":
    main()
