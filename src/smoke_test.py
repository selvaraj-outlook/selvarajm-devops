"""Send a KServe v2 (Open Inference Protocol) request and check the response.

    python src/smoke_test.py --url http://<kourier-lb> --host wine-classifier.models.example.com
"""

from __future__ import annotations

import argparse

import httpx

MODEL_NAME = "wine-classifier"
# Two rows from the wine dataset (13 features each).
SAMPLE = [
    [13.2, 1.78, 2.14, 11.2, 100.0, 2.65, 2.76, 0.26, 1.28, 4.38, 1.05, 3.4, 1050.0],
    [12.37, 0.94, 1.36, 10.6, 88.0, 1.98, 0.57, 0.28, 0.42, 1.95, 1.05, 1.82, 520.0],
]


def build_request(rows: list[list[float]]) -> dict:
    return {
        "inputs": [
            {
                "name": "input-0",
                "shape": [len(rows), len(rows[0])],
                "datatype": "FP32",
                "data": rows,
            }
        ]
    }


def predict(client: httpx.Client, rows: list[list[float]]) -> list[int]:
    response = client.post(f"/v2/models/{MODEL_NAME}/infer", json=build_request(rows))
    response.raise_for_status()
    outputs = response.json()["outputs"]
    return [int(v) for v in outputs[0]["data"]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--host", help="Host header when calling the Kourier load balancer directly")
    args = parser.parse_args()
    headers = {"Host": args.host} if args.host else {}
    with httpx.Client(base_url=args.url, headers=headers, timeout=30) as client:
        predictions = predict(client, SAMPLE)
    assert len(predictions) == len(SAMPLE), predictions
    assert all(p in (0, 1, 2) for p in predictions), predictions
    print("ok", predictions)


if __name__ == "__main__":
    main()
