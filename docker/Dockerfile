FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONPATH=/app/src MODEL_DIR=/app/model
ARG MODEL_VERSION=dev
ENV MODEL_VERSION=${MODEL_VERSION}
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt && useradd --uid 10001 --create-home app
COPY src/ /app/src/
COPY artifacts/model.joblib artifacts/metrics.json /app/model/
USER 10001
EXPOSE 8080
CMD ["uvicorn", "mlpipe.serve:app", "--host", "0.0.0.0", "--port", "8080"]
