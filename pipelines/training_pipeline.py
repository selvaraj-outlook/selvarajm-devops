"""Training pipeline: load -> train -> evaluate -> (gate) -> publish to S3."""

from kfp import compiler, dsl

from pipelines.components import evaluate_model, load_data, publish_model, train_model

PIPELINE_NAME = "breast-cancer-training"


@dsl.pipeline(name=PIPELINE_NAME, description="Train, evaluate and publish a random forest when it passes the gate.")
def training_pipeline(
    model_bucket: str,
    model_name: str = "breast-cancer-rf",
    n_estimators: int = 200,
    max_depth: int = 8,
    test_size: float = 0.2,
    min_accuracy: float = 0.93,
    seed: int = 42,
):
    data = load_data(test_size=test_size, seed=seed)

    train = train_model(train_data=data.outputs["train_data"], n_estimators=n_estimators, max_depth=max_depth)
    train.set_cpu_request("500m").set_memory_request("1Gi").set_memory_limit("2Gi")

    evaluation = evaluate_model(test_data=data.outputs["test_data"], model=train.outputs["model"])

    with dsl.If(evaluation.outputs["Output"] >= min_accuracy, name="accuracy-gate"):
        publish_model(
            model=train.outputs["model"],
            bucket=model_bucket,
            model_name=model_name,
            accuracy=evaluation.outputs["Output"],
        )


def compile_pipeline(path: str = "training_pipeline.yaml") -> str:
    compiler.Compiler().compile(training_pipeline, package_path=path)
    return path


if __name__ == "__main__":
    print(compile_pipeline())
