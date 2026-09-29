"""FastAPI model server. The model is baked into the image at build time."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

from mlpipe import FEATURES

MODEL_DIR = Path(os.environ.get("MODEL_DIR", "/app/model"))
app = FastAPI(title="credit-default", version=os.environ.get("MODEL_VERSION", "dev"))


class Applicant(BaseModel):
    income: float = Field(ge=0, le=5_000_000)
    debt_ratio: float = Field(ge=0, le=10)
    age: int = Field(ge=18, le=100)
    open_credit_lines: int = Field(ge=0, le=100)
    late_payments_90d: int = Field(ge=0, le=50)


class Prediction(BaseModel):
    default_probability: float
    model_version: str


@lru_cache(maxsize=1)
def model():
    return joblib.load(MODEL_DIR / "model.joblib")


@app.get("/health")
def health() -> dict:
    model()
    return {"status": "ok", "model_version": app.version}


@app.get("/metadata")
def metadata() -> dict:
    return json.loads((MODEL_DIR / "metrics.json").read_text())


@app.post("/predict", response_model=list[Prediction])
def predict(applicants: list[Applicant]) -> list[Prediction]:
    frame = pd.DataFrame([a.model_dump() for a in applicants])[FEATURES]
    probabilities = model().predict_proba(frame)[:, 1]
    return [Prediction(default_probability=round(float(p), 6), model_version=app.version) for p in probabilities]
