"""Generate synthetic hourly driver statistics as parquet.

    python scripts/generate_data.py --out data/driver_hourly_stats.parquet
    aws s3 cp data/driver_hourly_stats.parquet s3://<bucket>/data/
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd


def generate(drivers: int = 50, hours: int = 72, end: datetime | None = None, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    end = (end or datetime.now(UTC)).replace(minute=0, second=0, microsecond=0)
    timestamps = [end - timedelta(hours=h) for h in range(hours)]
    rows = []
    for driver_id in range(1001, 1001 + drivers):
        base_conv = rng.uniform(0.3, 0.9)
        for ts in timestamps:
            rows.append(
                {
                    "driver_id": driver_id,
                    "event_timestamp": ts,
                    "created": ts + timedelta(minutes=5),
                    "conv_rate": float(np.clip(base_conv + rng.normal(0, 0.05), 0, 1)),
                    "acc_rate": float(rng.uniform(0.6, 1.0)),
                    "avg_daily_trips": int(rng.integers(5, 40)),
                }
            )
    df = pd.DataFrame(rows)
    df["conv_rate"] = df["conv_rate"].astype("float32")
    df["acc_rate"] = df["acc_rate"].astype("float32")
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/driver_hourly_stats.parquet")
    parser.add_argument("--drivers", type=int, default=50)
    parser.add_argument("--hours", type=int, default=72)
    args = parser.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    generate(args.drivers, args.hours).to_parquet(args.out, index=False)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
