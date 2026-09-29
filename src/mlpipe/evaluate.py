"""Metrics and the champion/challenger promotion decision."""

from __future__ import annotations

from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

MIN_AUC = 0.70


def metrics(model, X, y) -> dict:
    proba = model.predict_proba(X)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(y, proba)),
        "pr_auc": float(average_precision_score(y, proba)),
        "brier": float(brier_score_loss(y, proba)),
    }


def should_promote(
    challenger: dict, champion: dict | None, min_auc: float = MIN_AUC, tolerance: float = 0.005
) -> tuple[bool, str]:
    """Promote if the challenger clears the absolute bar and does not regress the champion."""
    if challenger["roc_auc"] < min_auc:
        return False, f"roc_auc {challenger['roc_auc']:.4f} below minimum {min_auc}"
    if champion is None:
        return True, "no champion yet"
    if challenger["roc_auc"] + tolerance < champion["roc_auc"]:
        return False, f"roc_auc {challenger['roc_auc']:.4f} regresses champion {champion['roc_auc']:.4f}"
    if challenger["brier"] > champion["brier"] * 1.05:
        return False, f"calibration worse: brier {challenger['brier']:.4f} vs {champion['brier']:.4f}"
    return True, f"roc_auc {challenger['roc_auc']:.4f} vs champion {champion['roc_auc']:.4f}"
