import json
import re

from pipeline.definition import PipelineConfig, build_definition

CFG = PipelineConfig(
    role_arn="arn:aws:iam::123456789012:role/sm",
    bucket="bucket",
    code_prefix="code/abc",
    model_package_group="churn-models",
    sklearn_image="683313688378.dkr.ecr.us-east-1.amazonaws.com/sagemaker-scikit-learn:1.2-1-cpu-py3",
)


def _all_steps(steps):
    for step in steps:
        yield step
        if step["Type"] == "Condition":
            yield from _all_steps(step["Arguments"]["IfSteps"] + step["Arguments"]["ElseSteps"])


def _gets(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "Get":
                yield value
            else:
                yield from _gets(value)
    elif isinstance(node, list):
        for item in node:
            yield from _gets(item)


def test_definition_is_json_serialisable():
    json.dumps(build_definition(CFG))


def test_step_order_and_names():
    definition = build_definition(CFG)
    assert [s["Name"] for s in definition["Steps"]] == ["Preprocess", "Train", "Evaluate", "CheckAccuracy"]
    names = [s["Name"] for s in _all_steps(definition["Steps"])]
    assert len(names) == len(set(names))
    assert {"RegisterModel", "AccuracyBelowThreshold"} <= set(names)


def test_every_reference_points_to_a_defined_step_or_parameter():
    definition = build_definition(CFG)
    steps = {s["Name"] for s in _all_steps(definition["Steps"])}
    params = {p["Name"] for p in definition["Parameters"]}
    for ref in _gets(definition):
        kind, name = ref.split(".")[:2]
        if kind == "Steps":
            assert name in steps, ref
        elif kind == "Parameters":
            assert name in params, ref
        else:
            assert kind == "Execution", ref


def test_step_references_only_point_backwards():
    definition = build_definition(CFG)
    seen = set()
    for step in definition["Steps"]:
        for ref in _gets(step):
            match = re.match(r"Steps\.(\w+)", ref)
            if match:
                assert match.group(1) in seen, f"{step['Name']} references later step {ref}"
        seen.add(step["Name"])


def test_condition_gates_registration_on_accuracy():
    check = build_definition(CFG)["Steps"][-1]
    condition = check["Arguments"]["Conditions"][0]
    assert condition["Type"] == "GreaterThanOrEqualTo"
    assert condition["LeftValue"]["Std:JsonGet"]["Path"] == "metrics.accuracy.value"
    register = check["Arguments"]["IfSteps"][0]
    assert register["Arguments"]["ModelApprovalStatus"] == "PendingManualApproval"
    assert register["Arguments"]["ModelPackageGroupName"] == "churn-models"


def test_hyperparameters_are_strings_or_references():
    train = build_definition(CFG)["Steps"][1]
    for value in train["Arguments"]["HyperParameters"].values():
        assert isinstance(value, (str, dict))
