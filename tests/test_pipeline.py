from types import SimpleNamespace

import yaml

from pipelines import components
from pipelines.training_pipeline import compile_pipeline


class FakeArtifact(SimpleNamespace):
    def __init__(self, path):
        super().__init__(path=str(path), metadata={})


class FakeMetrics:
    def __init__(self):
        self.values = {}

    def log_metric(self, name, value):
        self.values[name] = value


def test_pipeline_compiles_with_gate(tmp_path):
    spec = yaml.safe_load(open(compile_pipeline(str(tmp_path / "p.yaml"))))
    tasks = spec["root"]["dag"]["tasks"]
    assert {"load-data", "train-model", "evaluate-model", "condition-1"} <= set(tasks)
    gate = tasks["condition-1"]
    assert "min_accuracy" in gate["triggerPolicy"]["condition"]
    inner = spec["components"]["comp-condition-1"]["dag"]["tasks"]
    assert "publish-model" in inner


def test_pipeline_parameters_have_defaults(tmp_path):
    spec = yaml.safe_load(open(compile_pipeline(str(tmp_path / "p.yaml"))))
    params = spec["root"]["inputDefinitions"]["parameters"]
    assert "defaultValue" not in params["model_bucket"]
    assert params["min_accuracy"]["defaultValue"] == 0.93


def test_components_run_end_to_end_locally(tmp_path):
    train_data, test_data = FakeArtifact(tmp_path / "train.csv"), FakeArtifact(tmp_path / "test.csv")
    components.load_data.python_func(test_size=0.2, seed=42, train_data=train_data, test_data=test_data)
    assert train_data.metadata["rows"] > test_data.metadata["rows"] > 0

    model = FakeArtifact(tmp_path / "model.joblib")
    components.train_model.python_func(train_data=train_data, n_estimators=50, max_depth=6, model=model)
    assert model.metadata["n_estimators"] == 50

    metrics = FakeMetrics()
    accuracy = components.evaluate_model.python_func(test_data=test_data, model=model, metrics=metrics)
    assert accuracy == metrics.values["accuracy"] > 0.9
    assert set(metrics.values) == {"accuracy", "f1", "roc_auc"}
