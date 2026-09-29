import boto3
import create_index
import run_eval
from botocore.stub import Stubber
from conftest import ingest_app

EVENT = {"Records": [{"s3": {"object": {"key": "handbook.md"}}}]}


def test_ingestion_started(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB12345678")
    monkeypatch.setenv("DATA_SOURCE_ID", "DS12345678")
    client = boto3.client("bedrock-agent", region_name="us-east-1")
    with Stubber(client) as stub:
        stub.add_response(
            "start_ingestion_job",
            {
                "ingestionJob": {
                    "knowledgeBaseId": "KB12345678",
                    "dataSourceId": "DS12345678",
                    "ingestionJobId": "JOB1234567",
                    "status": "STARTING",
                    "startedAt": "2026-01-01T00:00:00Z",
                    "updatedAt": "2026-01-01T00:00:00Z",
                }
            },
        )
        assert ingest_app.handler(EVENT, None, bedrock=client) == {"started": "JOB1234567", "keys": ["handbook.md"]}


def test_ingestion_conflict_is_ignored(monkeypatch):
    monkeypatch.setenv("KNOWLEDGE_BASE_ID", "KB12345678")
    monkeypatch.setenv("DATA_SOURCE_ID", "DS12345678")
    client = boto3.client("bedrock-agent", region_name="us-east-1")
    with Stubber(client) as stub:
        stub.add_client_error("start_ingestion_job", service_error_code="ConflictException")
        assert ingest_app.handler(EVENT, None, bedrock=client)["skipped"] == "ingestion already running"


def test_index_mapping_matches_terraform_field_mapping():
    props = create_index.index_body(1024)["mappings"]["properties"]
    assert props["embedding"]["dimension"] == 1024
    assert {"embedding", "text", "metadata"} == set(props)


def test_keyword_recall_and_scoring():
    assert run_eval.keyword_recall("Regions: US-EAST-1 and eu-west-1", ["us-east-1", "eu-west-1"]) == 1.0
    assert run_eval.keyword_recall("only us-east-1", ["us-east-1", "eu-west-1"]) == 0.5
    summary = run_eval.score([{"recall": 1.0, "cited": True}, {"recall": 0.5, "cited": False}])
    assert summary == {"questions": 2, "mean_recall": 0.75, "citation_rate": 0.5}
