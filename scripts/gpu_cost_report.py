"""Estimate the hourly cost of Karpenter-managed nodes, per NodePool.

    kubectl get nodes -o json | python scripts/gpu_cost_report.py
    kubectl get nodes -o json | python scripts/gpu_cost_report.py --prices prices.json --spot-discount 0.65

Prices are approximate us-east-1 On-Demand list prices (USD/hour). Pass
--prices with your own table for accurate numbers; Spot cost is estimated as
On-Demand x (1 - spot_discount).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict

DEFAULT_ON_DEMAND = {
    "g5.xlarge": 1.006,
    "g5.2xlarge": 1.212,
    "g5.4xlarge": 1.624,
    "g6.xlarge": 0.805,
    "g6.2xlarge": 0.978,
    "g6e.xlarge": 1.861,
    "m6i.large": 0.096,
    "m7i.large": 0.1008,
    "c7g.large": 0.0725,
    "m7g.large": 0.0816,
}


def summarize(nodes: dict, prices: dict[str, float], spot_discount: float) -> dict:
    pools: dict[str, dict] = defaultdict(lambda: {"nodes": 0, "gpus": 0, "spot": 0, "hourly_usd": 0.0, "unpriced": []})
    for node in nodes.get("items", []):
        labels = node["metadata"].get("labels", {})
        pool = labels.get("karpenter.sh/nodepool")
        if not pool:
            continue  # not managed by Karpenter
        instance = labels.get("node.kubernetes.io/instance-type", "unknown")
        capacity = labels.get("karpenter.sh/capacity-type", "on-demand")
        gpus = int(node.get("status", {}).get("capacity", {}).get("nvidia.com/gpu", 0))

        entry = pools[pool]
        entry["nodes"] += 1
        entry["gpus"] += gpus
        entry["spot"] += capacity == "spot"
        if instance in prices:
            price = prices[instance] * ((1 - spot_discount) if capacity == "spot" else 1)
            entry["hourly_usd"] += price
        else:
            entry["unpriced"].append(instance)

    total = sum(p["hourly_usd"] for p in pools.values())
    for p in pools.values():
        p["hourly_usd"] = round(p["hourly_usd"], 4)
    return {"pools": dict(pools), "total_hourly_usd": round(total, 4), "monthly_estimate_usd": round(total * 730, 2)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prices", help="JSON file mapping instance type to On-Demand USD/hour")
    parser.add_argument("--spot-discount", type=float, default=0.6)
    args = parser.parse_args()
    prices = dict(DEFAULT_ON_DEMAND)
    if args.prices:
        with open(args.prices) as f:
            prices.update(json.load(f))
    print(json.dumps(summarize(json.load(sys.stdin), prices, args.spot_discount), indent=2))


if __name__ == "__main__":
    main()
