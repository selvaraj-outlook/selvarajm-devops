FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir \
      "mlflow==2.17.2" \
      "psycopg2-binary==2.9.10" \
      "boto3==1.35.*" \
 && useradd --uid 10001 --create-home mlflow

COPY entrypoint.py /app/entrypoint.py

USER 10001
EXPOSE 5000
ENTRYPOINT ["python", "/app/entrypoint.py"]
