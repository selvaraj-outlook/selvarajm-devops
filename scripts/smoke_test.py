"""Smoke-test a deployed model service: health, metadata and a prediction."""

from __future__ import annotations

import argparse
import time

import httpx

APPLICANT = {"income": 52000, "debt_ratio": 0.4, "age": 35, "open_credit_lines": 5, "late_payments_90d": 0}


def check(client: httpx.Client, expected_version: str | None) -> None:
    health = client.get("/health").raise_for_status().json()
    if expected_version and health["model_version"] != expected_version:
        raise AssertionError(f"serving {health['model_version']}, expected {expected_version}")
    prediction = client.post("/predict", json=[APPLICANT]).raise_for_status().json()[0]
    assert 0.0 <= prediction["default_probability"] <= 1.0, prediction
    print(f"ok: version={health['model_version']} p={prediction['default_probability']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--version")
    parser.add_argument("--retries", type=int, default=30)
    args = parser.parse_args()
    with httpx.Client(base_url=args.url, timeout=10) as client:
        for attempt in range(args.retries):
            try:
                check(client, args.version)
                return
            except (httpx.HTTPError, AssertionError) as err:
                print(f"attempt {attempt + 1}: {err}")
                time.sleep(20)
    raise SystemExit("smoke test failed")


if __name__ == "__main__":
    main()
