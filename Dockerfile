FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir "feast[aws]==0.42.0" \
 && useradd --uid 10001 --create-home feast
COPY feature_repo/ /app/feature_repo/
WORKDIR /app/feature_repo
USER 10001
ENTRYPOINT ["feast"]
CMD ["--help"]
