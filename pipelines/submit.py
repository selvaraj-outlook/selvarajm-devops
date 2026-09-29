"""Compile and submit the pipeline to a Kubeflow Pipelines endpoint.

    kubectl -n kubeflow port-forward svc/ml-pipeline-ui 8080:80
    python -m pipelines.submit --host http://localhost:8080 --bucket <model_bucket>
"""

from __future__ import annotations

import argparse

import kfp

from pipelines.training_pipeline import PIPELINE_NAME, training_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--experiment", default="training")
    parser.add_argument("--n-estimators", type=int, default=200)
    parser.add_argument("--wait", action="store_true")
    args = parser.parse_args()

    client = kfp.Client(host=args.host)
    run = client.create_run_from_pipeline_func(
        training_pipeline,
        arguments={"model_bucket": args.bucket, "n_estimators": args.n_estimators},
        experiment_name=args.experiment,
        run_name=f"{PIPELINE_NAME}-{args.n_estimators}",
        service_account="pipeline-runner",
    )
    print(f"run: {run.run_id}")
    if args.wait:
        result = client.wait_for_run_completion(run.run_id, timeout=3600)
        print(f"state: {result.state}")
        if result.state != "SUCCEEDED":
            raise SystemExit(1)


if __name__ == "__main__":
    main()
