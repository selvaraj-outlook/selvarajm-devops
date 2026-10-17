FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /mlops

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src

RUN useradd --create-home --uid 10001 mlops
USER mlops

# Run either script, e.g.:
#   docker run --rm <image> src/publish_model.py --bucket <bucket> --version v2
#   docker run --rm <image> src/smoke_test.py --url http://<lb> --host <host>
ENTRYPOINT ["python"]
CMD ["src/publish_model.py", "--help"]
