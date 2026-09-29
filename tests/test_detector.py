import numpy as np
import pandas as pd

from drift import detector

RNG = np.random.default_rng(0)


def _frame(n: int, shift: float = 0.0, city_probs=(0.5, 0.3, 0.2)) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "amount": RNG.normal(100 + shift, 15, n),
            "age": RNG.normal(40, 10, n),
            "city": RNG.choice(["a", "b", "c"], n, p=city_probs),
        }
    )


def test_psi_is_zero_for_identical_distributions():
    x = RNG.normal(0, 1, 5000)
    assert detector.psi_numeric(x, x) < 1e-9


def test_psi_grows_with_shift():
    x = RNG.normal(0, 1, 5000)
    small = detector.psi_numeric(x, RNG.normal(0.1, 1, 5000))
    large = detector.psi_numeric(x, RNG.normal(1.0, 1, 5000))
    assert small < 0.1 < 0.2 < large


def test_no_drift_on_same_distribution():
    report = detector.detect(_frame(3000), _frame(3000))
    assert report.drift_share == 0
    assert not report.dataset_drifted()


def test_numeric_and_categorical_drift_detected():
    report = detector.detect(_frame(3000), _frame(3000, shift=20, city_probs=(0.1, 0.2, 0.7)))
    by_name = {f.feature: f for f in report.features}
    assert by_name["amount"].drifted and by_name["amount"].kind == "numeric"
    assert by_name["city"].drifted and by_name["city"].kind == "categorical"
    assert not by_name["age"].drifted
    assert report.drift_share == 2 / 3
    assert report.dataset_drifted(0.5)


def test_unseen_category_is_handled():
    ref = pd.Series(["a", "b"] * 100)
    cur = pd.Series(["a", "b", "z"] * 100)
    assert detector.psi_categorical(ref, cur) > 0.2
