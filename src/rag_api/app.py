"""RAG question-answering API (AWS Lambda, function URL with IAM auth).

POST {"question": "...", "session_id": "optional"}
->   {"answer": "...", "citations": [{"source": "s3://...", "excerpt": "..."}], "session_id": "..."}
"""

from __future__ import annotations

import json
import os

import boto3

MAX_QUESTION_CHARS = 2000
client = boto3.client("bedrock-agent-runtime")


class BadRequest(ValueError):
    pass


def parse_request(event: dict) -> tuple[str, str | None]:
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as err:
        raise BadRequest("body must be JSON") from err
    question = (body.get("question") or "").strip()
    if not question:
        raise BadRequest("'question' is required")
    if len(question) > MAX_QUESTION_CHARS:
        raise BadRequest(f"'question' must be at most {MAX_QUESTION_CHARS} characters")
    return question, body.get("session_id")


def build_request(question: str, session_id: str | None, env: dict) -> dict:
    request = {
        "input": {"text": question},
        "retrieveAndGenerateConfiguration": {
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": env["KNOWLEDGE_BASE_ID"],
                "modelArn": env["MODEL_ARN"],
                "retrievalConfiguration": {
                    "vectorSearchConfiguration": {"numberOfResults": int(env.get("TOP_K", "5"))}
                },
                "generationConfiguration": {
                    "guardrailConfiguration": {
                        "guardrailId": env["GUARDRAIL_ID"],
                        "guardrailVersion": env["GUARDRAIL_VERSION"],
                    },
                    "inferenceConfig": {"textInferenceConfig": {"temperature": 0.0, "maxTokens": 800}},
                },
            },
        },
    }
    if session_id:
        request["sessionId"] = session_id
    return request


def format_response(response: dict) -> dict:
    citations = []
    for citation in response.get("citations", []):
        for ref in citation.get("retrievedReferences", []):
            citations.append(
                {
                    "source": ref.get("location", {}).get("s3Location", {}).get("uri"),
                    "excerpt": ref.get("content", {}).get("text", "")[:300],
                }
            )
    return {"answer": response["output"]["text"], "citations": citations, "session_id": response.get("sessionId")}


def _http(status: int, body: dict) -> dict:
    return {"statusCode": status, "headers": {"content-type": "application/json"}, "body": json.dumps(body)}


def handler(event, _context, bedrock=None):
    bedrock = bedrock or client
    try:
        question, session_id = parse_request(event)
    except BadRequest as err:
        return _http(400, {"error": str(err)})
    response = bedrock.retrieve_and_generate(**build_request(question, session_id, dict(os.environ)))
    return _http(200, format_response(response))
