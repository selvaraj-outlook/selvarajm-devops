"""Upload a reference snapshot and one day of (optionally shifted) inference data.

python scripts/seed_demo_data.py --bucket <data_bucket> --shift 15
"""

from __future__ import annotations

import argparse
import io
from datetime import UTC, datetime

import boto3
import numpy as np
import pandas as pd


def make(n: int, shift: float, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "amount": rng.lognormal(4 + shift / 100, 0.6, n),
            "account_age_days": rng.integers(1, 3650, n),
            "hour": rng.integers(0, 24, n),
            "merchant_category": rng.choice(["grocery", "travel", "online", "fuel"], n, p=[0.4, 0.1, 0.35, 0.15]),
            "velocity_1h": rng.poisson(1 + shift / 10, n),
        }
    )


def upload(s3, bucket: str, key: str, df: pd.DataFrame) -> None:
    buf = io.BytesIO()
    df.to_parquet(buf, index=False)
    s3.put_object(Bucket=bucket, Key=key, Body=buf.getvalue())
    print(f"s3://{bucket}/{key} ({len(df)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--shift", type=float, default=0.0, help="0 = no drift; 15+ = clear drift")
    args = parser.parse_args()
    s3 = boto3.client("s3")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    upload(s3, args.bucket, "reference/train.parquet", make(20000, 0, seed=1))
    upload(s3, args.bucket, f"inference/date={today}/part-0.parquet", make(5000, args.shift, seed=2))


if __name__ == "__main__":
    main()
