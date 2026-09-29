"""Statistical drift detection between a reference and a current dataset.

Numeric features: Population Stability Index (PSI) and the two-sample
Kolmogorov-Smirnov test. Categorical features: PSI over categories and the
chi-square test. A feature is flagged as drifted when its PSI crosses the
threshold or its p-value falls below alpha.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy import stats

EPS = 1e-6


@dataclass(frozen=True)
class FeatureDrift:
    feature: str
    kind: str  # "numeric" | "categorical"
    psi: float
    p_value: float
    drifted: bool


@dataclass(frozen=True)
class DriftReport:
    features: list[FeatureDrift]
    reference_rows: int
    current_rows: int

    @property
    def drift_share(self) -> float:
        return sum(f.drifted for f in self.features) / len(self.features) if self.features else 0.0

    def dataset_drifted(self, share_threshold: float = 0.3) -> bool:
        return self.drift_share >= share_threshold

    def to_dict(self) -> dict:
        return {
            "reference_rows": self.reference_rows,
            "current_rows": self.current_rows,
            "drift_share": self.drift_share,
            "features": [asdict(f) for f in self.features],
        }


def psi_numeric(reference: np.ndarray, current: np.ndarray, bins: int = 10) -> float:
    """PSI with quantile bins taken from the reference distribution."""
    reference, current = reference[~np.isnan(reference)], current[~np.isnan(current)]
    edges = np.unique(np.quantile(reference, np.linspace(0, 1, bins + 1)))
    if len(edges) < 2:
        return 0.0
    edges[0], edges[-1] = -np.inf, np.inf
    ref_pct = np.histogram(reference, edges)[0] / len(reference)
    cur_pct = np.histogram(current, edges)[0] / len(current)
    return _psi(ref_pct, cur_pct)


def psi_categorical(reference: pd.Series, current: pd.Series) -> float:
    categories = sorted(set(reference.dropna()) | set(current.dropna()), key=str)
    ref_pct = reference.value_counts(normalize=True).reindex(categories, fill_value=0).to_numpy()
    cur_pct = current.value_counts(normalize=True).reindex(categories, fill_value=0).to_numpy()
    return _psi(ref_pct, cur_pct)


def _psi(ref_pct: np.ndarray, cur_pct: np.ndarray) -> float:
    ref_pct, cur_pct = np.clip(ref_pct, EPS, None), np.clip(cur_pct, EPS, None)
    return float(np.sum((cur_pct - ref_pct) * np.log(cur_pct / ref_pct)))


def chi2_p_value(reference: pd.Series, current: pd.Series) -> float:
    categories = sorted(set(reference.dropna()) | set(current.dropna()), key=str)
    table = np.array(
        [
            reference.value_counts().reindex(categories, fill_value=0).to_numpy(),
            current.value_counts().reindex(categories, fill_value=0).to_numpy(),
        ]
    )
    table = table[:, table.sum(axis=0) > 0]
    if table.shape[1] < 2:
        return 1.0
    return float(stats.chi2_contingency(table)[1])


def detect(
    reference: pd.DataFrame,
    current: pd.DataFrame,
    features: list[str] | None = None,
    psi_threshold: float = 0.2,
    alpha: float = 0.01,
) -> DriftReport:
    features = features or [c for c in reference.columns if c in current.columns]
    results = []
    for name in features:
        ref, cur = reference[name], current[name]
        if pd.api.types.is_numeric_dtype(ref) and ref.nunique() > 10:
            psi = psi_numeric(ref.to_numpy(dtype=float), cur.to_numpy(dtype=float))
            p_value = float(stats.ks_2samp(ref.dropna(), cur.dropna()).pvalue)
            kind = "numeric"
        else:
            psi = psi_categorical(ref.astype(str), cur.astype(str))
            p_value = chi2_p_value(ref.astype(str), cur.astype(str))
            kind = "categorical"
        results.append(FeatureDrift(name, kind, psi, p_value, psi >= psi_threshold or p_value < alpha))
    return DriftReport(results, len(reference), len(current))
