import io
import json
import tarfile

import evaluate
import joblib
import pandas as pd
import preprocess
import train
from sklearn.datasets import load_breast_cancer


def _data() -> pd.DataFrame:
    X, y = load_breast_cancer(return_X_y=True, as_frame=True)
    return X.assign(target=y)


def test_preprocess_splits_stratified(tmp_path, monkeypatch):
    raw = tmp_path / "input" / "raw"
    raw.mkdir(parents=True)
    _data().to_csv(raw / "data.csv", index=False)
    monkeypatch.setattr("sys.argv", ["preprocess.py", "--test-size", "0.25"])
    preprocess.main(base=str(tmp_path))
    tr = pd.read_csv(tmp_path / "train" / "train.csv")
    te = pd.read_csv(tmp_path / "test" / "test.csv")
    assert len(tr) + len(te) == len(_data().drop_duplicates())
    assert abs(tr["target"].mean() - te["target"].mean()) < 0.05


def test_train_and_evaluate_end_to_end(tmp_path):
    train_df, test_df = preprocess.split(_data(), 0.25, 42)
    model = train.fit(train_df, n_estimators=50, learning_rate=0.1, max_depth=3)

    model_dir = tmp_path / "model"
    model_dir.mkdir()
    buffer = io.BytesIO()
    joblib.dump(model, buffer)
    with tarfile.open(model_dir / "model.tar.gz", "w:gz") as tar:
        info = tarfile.TarInfo("model.joblib")
        info.size = len(buffer.getvalue())
        tar.addfile(info, io.BytesIO(buffer.getvalue()))
    (tmp_path / "test").mkdir()
    test_df.to_csv(tmp_path / "test" / "test.csv", index=False)

    evaluate.main(base=str(tmp_path))
    report = json.loads((tmp_path / "evaluation" / "evaluation.json").read_text())
    assert report["metrics"]["accuracy"]["value"] > 0.9
