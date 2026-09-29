import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import gpu_cost_report  # noqa: E402


def node(pool, instance, capacity, gpus=0):
    labels = {"node.kubernetes.io/instance-type": instance, "karpenter.sh/capacity-type": capacity}
    if pool:
        labels["karpenter.sh/nodepool"] = pool
    return {"metadata": {"labels": labels}, "status": {"capacity": {"nvidia.com/gpu": str(gpus)} if gpus else {}}}


def test_costs_grouped_by_pool_with_spot_discount():
    nodes = {
        "items": [
            node("gpu-inference", "g5.xlarge", "spot", gpus=1),
            node("gpu-inference", "g5.xlarge", "on-demand", gpus=1),
            node("general", "m7i.large", "on-demand"),
            node(None, "m5.large", "on-demand"),  # managed node group, ignored
        ]
    }
    report = gpu_cost_report.summarize(nodes, {"g5.xlarge": 1.0, "m7i.large": 0.1}, spot_discount=0.6)
    gpu = report["pools"]["gpu-inference"]
    assert gpu["nodes"] == 2 and gpu["gpus"] == 2 and gpu["spot"] == 1
    assert gpu["hourly_usd"] == pytest.approx(1.4)
    assert report["pools"]["general"]["hourly_usd"] == pytest.approx(0.1)
    assert report["total_hourly_usd"] == pytest.approx(1.5)
    assert report["monthly_estimate_usd"] == pytest.approx(1095.0)


def test_unknown_instance_types_are_reported_not_guessed():
    report = gpu_cost_report.summarize({"items": [node("gpu-inference", "p5.48xlarge", "on-demand", 8)]}, {}, 0.6)
    assert report["pools"]["gpu-inference"]["unpriced"] == ["p5.48xlarge"]
    assert report["total_hourly_usd"] == 0
