import json

import boto3
from botocore.stub import ANY, Stubber
from conftest import rag_app

ENV = {
    "KNOWLEDGE_BASE_ID": "KB12345678",
    "MODEL_ARN": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0",
    "GUARDRAIL_ID": "gr123456789",
    "GUARDRAIL_VERSION": "1",
}


def test_rejects_missing_question():
    response = rag_app.handler({"body": json.dumps({})}, None, bedrock=object())
    assert response["statusCode"] == 400


def test_rejects_oversized_question():
    body = json.dumps({"question": "x" * 3000})
    assert rag_app.handler({"body": body}, None, bedrock=object())["statusCode"] == 400


def test_request_includes_guardrail_and_session():
    request = rag_app.build_request("q?", "sess-1", ENV)
    kb = request["retrieveAndGenerateConfiguration"]["knowledgeBaseConfiguration"]
    assert kb["generationConfiguration"]["guardrailConfiguration"] == {
        "guardrailId": "gr123456789",
        "guardrailVersion": "1",
    }
    assert request["sessionId"] == "sess-1"


def test_answer_with_citations(monkeypatch):
    for key, value in ENV.items():
        monkeypatch.setenv(key, value)
    client = boto3.client("bedrock-agent-runtime", region_name="us-east-1")
    with Stubber(client) as stub:
        stub.add_response(
            "retrieve_and_generate",
            {
                "sessionId": "sess-9",
                "output": {"text": "Employees get 25 days of annual leave."},
                "citations": [
                    {
                        "retrievedReferences": [
                            {
                                "content": {"text": "Full-time employees receive 25 days..."},
                                "location": {"type": "S3", "s3Location": {"uri": "s3://docs/handbook.md"}},
                            }
                        ]
                    }
                ],
            },
            {"input": {"text": "How much leave?"}, "retrieveAndGenerateConfiguration": ANY},
        )
        response = rag_app.handler({"body": json.dumps({"question": "How much leave?"})}, None, bedrock=client)
    body = json.loads(response["body"])
    assert response["statusCode"] == 200
    assert body["answer"].startswith("Employees get 25 days")
    assert body["citations"] == [
        {"source": "s3://docs/handbook.md", "excerpt": "Full-time employees receive 25 days..."}
    ]
    assert body["session_id"] == "sess-9"
