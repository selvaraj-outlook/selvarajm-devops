"""SageMaker Processing: split the raw CSV into train/test sets.

Input:  /opt/ml/processing/input/raw/*.csv  (label column: "target")
Output: /opt/ml/processing/train/train.csv, /opt/ml/processing/test/test.csv
"""

from __future__ import annotations

import argparse
import glob
import os

import pandas as pd
from sklearn.model_selection import train_test_split

BASE = "/opt/ml/processing"


def split(df: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.dropna().drop_duplicates()
    if "target" not in df.columns:
        raise ValueError("input data must contain a 'target' column")
    return train_test_split(df, test_size=test_size, random_state=seed, stratify=df["target"])


def main(base: str = BASE) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--test-size", type=float, default=0.2)
    parser.add_argument("--seed", type=int, default=42)
    args, _ = parser.parse_known_args()

    files = glob.glob(os.path.join(base, "input", "raw", "*.csv"))
    if not files:
        raise FileNotFoundError("no CSV files in input/raw")
    df = pd.concat(pd.read_csv(f) for f in files)
    train, test = split(df, args.test_size, args.seed)

    for name, frame in (("train", train), ("test", test)):
        os.makedirs(os.path.join(base, name), exist_ok=True)
        frame.to_csv(os.path.join(base, name, f"{name}.csv"), index=False)
    print(f"train={len(train)} test={len(test)}")


if __name__ == "__main__":
    main()
