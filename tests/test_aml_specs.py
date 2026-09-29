"""Static checks that the Azure ML YAML specs are wired together correctly."""

import json
import re
from pathlib import Path

import yaml

AML = Path(__file__).resolve().parents[1] / "aml"


def load(path):
    return yaml.safe_load((AML / path).read_text())


def test_pipeline_steps_reference_existing_components_and_outputs():
    pipeline = load("pipeline.yaml")
    outputs = {}
    for name, job in pipeline["jobs"].items():
        component = load(job["component"].removeprefix("./"))
        outputs[name] = set(component.get("outputs", {}))
        declared_inputs = set(component["inputs"])
        assert set(job.get("inputs", {})) <= declared_inputs, name
        for value in job.get("inputs", {}).values():
            match = re.match(r"\$\{\{parent\.jobs\.(\w+)\.outputs\.(\w+)\}\}", str(value))
            if match:
                assert match.group(2) in outputs[match.group(1)], value


def test_component_commands_use_declared_io_and_code_exists():
    for path in (AML / "components").glob("*.yaml"):
        component = yaml.safe_load(path.read_text())
        declared = set(component["inputs"]) | set(component.get("outputs", {}))
        used = set(re.findall(r"\$\{\{(?:inputs|outputs)\.(\w+)\}\}", component["command"]))
        assert used == declared, path.name
        assert (path.parent / component["code"]).resolve().is_dir(), path.name


def test_sample_request_matches_training_features():
    import make_data

    request = json.loads((AML / "endpoints" / "sample-request.json").read_text())
    assert request["input_data"]["columns"] == make_data.FEATURES
