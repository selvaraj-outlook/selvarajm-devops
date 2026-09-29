"""Inference handler for the SageMaker scikit-learn serving container."""

import os

import joblib


def model_fn(model_dir):
    return joblib.load(os.path.join(model_dir, "model.joblib"))
