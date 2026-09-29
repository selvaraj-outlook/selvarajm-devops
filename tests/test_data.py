from mlpipe.data import synthetic, validate


def test_synthetic_data_passes_validation():
    assert validate(synthetic()).ok


def test_validation_catches_bad_data():
    df = synthetic(1000)
    df.loc[:20, "age"] = 7
    df.loc[:30, "income"] = None
    df = df.drop(columns=["late_payments_90d"])
    assert validate(df).errors == ["missing columns: ['late_payments_90d']"]


def test_validation_reports_every_rule():
    df = synthetic(1000)
    df.loc[:20, "age"] = 7
    df.loc[:30, "income"] = None
    errors = validate(df).errors
    assert any(e.startswith("age: 21 values outside") for e in errors)
    assert any(e.startswith("income:") and "nulls" in e for e in errors)


def test_too_few_rows():
    assert "only 100 rows" in validate(synthetic(100), min_rows=500).errors[0]
