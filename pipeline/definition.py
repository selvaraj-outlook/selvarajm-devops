"""Build the SageMaker Pipeline definition as plain JSON (no SageMaker SDK).

Steps: Preprocess -> Train -> Evaluate -> CheckAccuracy
          if accuracy >= threshold: RegisterModel (PendingManualApproval)
          else:                     Fail
"""

from __future__ import annotations

from dataclasses import dataclass

PROCESSING = "/opt/ml/processing"


@dataclass(frozen=True)
class PipelineConfig:
    role_arn: str
    bucket: str
    code_prefix: str  # s3 prefix holding the uploaded scripts and sourcedir.tar.gz
    model_package_group: str
    sklearn_image: str
    processing_instance: str = "ml.m5.large"
    training_instance: str = "ml.m5.large"


def _get(path: str) -> dict:
    return {"Get": path}


def _processing_output(name: str, s3_uri, local: str) -> dict:
    return {
        "OutputName": name,
        "AppManaged": False,
        "S3Output": {"S3Uri": s3_uri, "LocalPath": local, "S3UploadMode": "EndOfJob"},
    }


def _processing_input(name: str, s3_uri, local: str) -> dict:
    return {
        "InputName": name,
        "AppManaged": False,
        "S3Input": {
            "S3Uri": s3_uri,
            "LocalPath": local,
            "S3DataType": "S3Prefix",
            "S3InputMode": "File",
            "S3DataDistributionType": "FullyReplicated",
        },
    }


def _join(*parts) -> dict:
    return {"Std:Join": {"On": "/", "Values": list(parts)}}


def build_definition(cfg: PipelineConfig) -> dict:
    code = f"s3://{cfg.bucket}/{cfg.code_prefix}"
    run_prefix = _join(f"s3://{cfg.bucket}", "runs", _get("Execution.PipelineExecutionId"))
    resources = {
        "ClusterConfig": {
            "InstanceCount": 1,
            "InstanceType": _get("Parameters.ProcessingInstanceType"),
            "VolumeSizeInGB": 30,
        }
    }

    preprocess = {
        "Name": "Preprocess",
        "Type": "Processing",
        "Arguments": {
            "RoleArn": cfg.role_arn,
            "AppSpecification": {
                "ImageUri": cfg.sklearn_image,
                "ContainerEntrypoint": ["python3", f"{PROCESSING}/input/code/preprocess.py"],
            },
            "ProcessingResources": resources,
            "ProcessingInputs": [
                _processing_input("raw", _get("Parameters.InputDataUri"), f"{PROCESSING}/input/raw"),
                _processing_input("code", f"{code}/preprocess.py", f"{PROCESSING}/input/code"),
            ],
            "ProcessingOutputConfig": {
                "Outputs": [
                    _processing_output("train", _join(run_prefix, "train"), f"{PROCESSING}/train"),
                    _processing_output("test", _join(run_prefix, "test"), f"{PROCESSING}/test"),
                ]
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
        },
    }

    train = {
        "Name": "Train",
        "Type": "Training",
        "Arguments": {
            "RoleArn": cfg.role_arn,
            "AlgorithmSpecification": {"TrainingImage": cfg.sklearn_image, "TrainingInputMode": "File"},
            # Framework containers expect JSON-encoded hyperparameter values.
            "HyperParameters": {
                "sagemaker_program": '"train.py"',
                "sagemaker_submit_directory": f'"{code}/sourcedir.tar.gz"',
                "n_estimators": _get("Parameters.NEstimators"),
                "learning_rate": _get("Parameters.LearningRate"),
            },
            "InputDataConfig": [
                {
                    "ChannelName": "train",
                    "ContentType": "text/csv",
                    "DataSource": {
                        "S3DataSource": {
                            "S3DataType": "S3Prefix",
                            "S3Uri": _get("Steps.Preprocess.ProcessingOutputConfig.Outputs['train'].S3Output.S3Uri"),
                            "S3DataDistributionType": "FullyReplicated",
                        }
                    },
                }
            ],
            "OutputDataConfig": {"S3OutputPath": _join(run_prefix, "model")},
            "ResourceConfig": {
                "InstanceCount": 1,
                "InstanceType": _get("Parameters.TrainingInstanceType"),
                "VolumeSizeInGB": 30,
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": 3600},
        },
    }

    evaluate = {
        "Name": "Evaluate",
        "Type": "Processing",
        "Arguments": {
            "RoleArn": cfg.role_arn,
            "AppSpecification": {
                "ImageUri": cfg.sklearn_image,
                "ContainerEntrypoint": ["python3", f"{PROCESSING}/input/code/evaluate.py"],
            },
            "ProcessingResources": resources,
            "ProcessingInputs": [
                _processing_input("model", _get("Steps.Train.ModelArtifacts.S3ModelArtifacts"), f"{PROCESSING}/model"),
                _processing_input(
                    "test",
                    _get("Steps.Preprocess.ProcessingOutputConfig.Outputs['test'].S3Output.S3Uri"),
                    f"{PROCESSING}/test",
                ),
                _processing_input("code", f"{code}/evaluate.py", f"{PROCESSING}/input/code"),
            ],
            "ProcessingOutputConfig": {
                "Outputs": [
                    _processing_output("evaluation", _join(run_prefix, "evaluation"), f"{PROCESSING}/evaluation")
                ]
            },
            "StoppingCondition": {"MaxRuntimeInSeconds": 1800},
        },
        "PropertyFiles": [
            {"PropertyFileName": "EvaluationReport", "OutputName": "evaluation", "FilePath": "evaluation.json"}
        ],
    }

    register = {
        "Name": "RegisterModel",
        "Type": "RegisterModel",
        "Arguments": {
            "ModelPackageGroupName": cfg.model_package_group,
            "ModelApprovalStatus": "PendingManualApproval",
            "InferenceSpecification": {
                "Containers": [
                    {
                        "Image": cfg.sklearn_image,
                        "ModelDataUrl": _get("Steps.Train.ModelArtifacts.S3ModelArtifacts"),
                        "Environment": {
                            "SAGEMAKER_PROGRAM": "inference.py",
                            "SAGEMAKER_SUBMIT_DIRECTORY": f"{code}/sourcedir.tar.gz",
                        },
                    }
                ],
                "SupportedContentTypes": ["text/csv"],
                "SupportedResponseMIMETypes": ["text/csv"],
                "SupportedRealtimeInferenceInstanceTypes": ["ml.t2.medium", "ml.m5.large"],
                "SupportedTransformInstanceTypes": ["ml.m5.large"],
            },
            "ModelMetrics": {
                "ModelQuality": {
                    "Statistics": {
                        "ContentType": "application/json",
                        "S3Uri": _join(run_prefix, "evaluation", "evaluation.json"),
                    }
                }
            },
        },
    }

    fail = {
        "Name": "AccuracyBelowThreshold",
        "Type": "Fail",
        "Arguments": {"ErrorMessage": "Model accuracy is below the registration threshold."},
    }

    check = {
        "Name": "CheckAccuracy",
        "Type": "Condition",
        "Arguments": {
            "Conditions": [
                {
                    "Type": "GreaterThanOrEqualTo",
                    "LeftValue": {
                        "Std:JsonGet": {
                            "PropertyFile": _get("Steps.Evaluate.PropertyFiles.EvaluationReport"),
                            "Path": "metrics.accuracy.value",
                        }
                    },
                    "RightValue": _get("Parameters.AccuracyThreshold"),
                }
            ],
            "IfSteps": [register],
            "ElseSteps": [fail],
        },
    }

    return {
        "Version": "2020-12-01",
        "Metadata": {},
        "Parameters": [
            {"Name": "InputDataUri", "Type": "String", "DefaultValue": f"s3://{cfg.bucket}/data/raw"},
            {"Name": "ProcessingInstanceType", "Type": "String", "DefaultValue": cfg.processing_instance},
            {"Name": "TrainingInstanceType", "Type": "String", "DefaultValue": cfg.training_instance},
            {"Name": "NEstimators", "Type": "String", "DefaultValue": "150"},
            {"Name": "LearningRate", "Type": "String", "DefaultValue": "0.1"},
            {"Name": "AccuracyThreshold", "Type": "Float", "DefaultValue": 0.85},
        ],
        "PipelineExperimentConfig": {
            "ExperimentName": _get("Execution.PipelineName"),
            "TrialName": _get("Execution.PipelineExecutionId"),
        },
        "Steps": [preprocess, train, evaluate, check],
    }
