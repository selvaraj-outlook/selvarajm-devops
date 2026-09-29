"""Prepare data: clean, split and write train/test CSVs."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split

TARGET = "target"


def prepare(df: pd.DataFrame, test_size: float, seed: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.dropna().drop_duplicates()
    return train_test_split(df, test_size=test_size, random_state=seed, stratify=df[TARGET])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw_data", required=True)
    parser.add_argument("--test_size", type=float, default=0.2)
    parser.add_argument("--train_data", required=True)
    parser.add_argument("--test_data", required=True)
    args = parser.parse_args()

    raw = Path(args.raw_data)
    files = [raw] if raw.is_file() else sorted(raw.glob("*.csv"))
    df = pd.concat(pd.read_csv(f) for f in files)
    train, test = prepare(df, args.test_size, seed=42)
    for frame, out in ((train, args.train_data), (test, args.test_data)):
        Path(out).mkdir(parents=True, exist_ok=True)
        frame.to_csv(Path(out) / "data.csv", index=False)
    print(f"train={len(train)} test={len(test)}")


if __name__ == "__main__":
    main()
