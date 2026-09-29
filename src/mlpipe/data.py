"""Load and validate training data. Validation fails the pipeline early."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from mlpipe import FEATURES, TARGET

RULES = {
    "income": (0, 5_000_000),
    "debt_ratio": (0, 10),
    "age": (18, 100),
    "open_credit_lines": (0, 100),
    "late_payments_90d": (0, 50),
}


@dataclass
class ValidationResult:
    errors: list[str]

    @property
    def ok(self) -> bool:
        return not self.errors


def validate(df: pd.DataFrame, min_rows: int = 500, max_null_share: float = 0.01) -> ValidationResult:
    errors = []
    missing = [c for c in [*FEATURES, TARGET] if c not in df.columns]
    if missing:
        return ValidationResult([f"missing columns: {missing}"])
    if len(df) < min_rows:
        errors.append(f"only {len(df)} rows (minimum {min_rows})")
    for column in [*FEATURES, TARGET]:
        null_share = df[column].isna().mean()
        if null_share > max_null_share:
            errors.append(f"{column}: {null_share:.1%} nulls (max {max_null_share:.0%})")
    for column, (low, high) in RULES.items():
        out = (~df[column].dropna().between(low, high)).sum()
        if out:
            errors.append(f"{column}: {out} values outside [{low}, {high}]")
    if not set(df[TARGET].dropna().unique()) <= {0, 1}:
        errors.append(f"{TARGET} must be binary 0/1")
    positive = df[TARGET].mean()
    if not 0.01 <= positive <= 0.5:
        errors.append(f"{TARGET} positive rate {positive:.1%} outside expected 1%-50%")
    return ValidationResult(errors)


def synthetic(n: int = 5000, seed: int = 0) -> pd.DataFrame:
    """Synthetic credit data with a known signal, for demos and tests."""
    rng = np.random.default_rng(seed)
    df = pd.DataFrame(
        {
            "income": rng.lognormal(10.8, 0.5, n).round(0),
            "debt_ratio": rng.gamma(2.0, 0.2, n).clip(0, 10),
            "age": rng.integers(21, 75, n),
            "open_credit_lines": rng.poisson(6, n),
            "late_payments_90d": rng.poisson(0.3, n),
        }
    )
    logit = -1.5 + 3.0 * df["debt_ratio"] + 1.2 * df["late_payments_90d"] - 0.00003 * df["income"] - 0.02 * df["age"]
    df[TARGET] = (rng.random(n) < 1 / (1 + np.exp(-logit))).astype(int)
    return df
