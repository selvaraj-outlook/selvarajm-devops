"""Offline RAG evaluation against a golden question set.

Calls the knowledge base directly and scores each answer by keyword recall
and by whether it cites at least one source. Fails (exit 1) below the gate.

    python eval/run_eval.py --kb-id <id> --model-arn <arn> --min-score 0.75
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import boto3


def keyword_recall(answer: str, expected: list[str]) -> float:
    text = answer.lower()
    return sum(k.lower() in text for k in expected) / len(expected) if expected else 1.0


def score(results: list[dict]) -> dict:
    recall = [r["recall"] for r in results]
    cited = [r["cited"] for r in results]
    return {
        "questions": len(results),
        "mean_recall": sum(recall) / len(recall) if recall else 0.0,
        "citation_rate": sum(cited) / len(cited) if cited else 0.0,
    }


def ask(client, kb_id: str, model_arn: str, question: str) -> dict:
    response = client.retrieve_and_generate(
        input={"text": question},
        retrieveAndGenerateConfiguration={
            "type": "KNOWLEDGE_BASE",
            "knowledgeBaseConfiguration": {"knowledgeBaseId": kb_id, "modelArn": model_arn},
        },
    )
    refs = [r for c in response.get("citations", []) for r in c.get("retrievedReferences", [])]
    return {"answer": response["output"]["text"], "cited": bool(refs)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kb-id", required=True)
    parser.add_argument("--model-arn", required=True)
    parser.add_argument("--golden", default=str(Path(__file__).with_name("golden.json")))
    parser.add_argument("--min-score", type=float, default=0.75)
    args = parser.parse_args()

    client = boto3.client("bedrock-agent-runtime")
    results = []
    for item in json.loads(Path(args.golden).read_text()):
        result = ask(client, args.kb_id, args.model_arn, item["question"])
        result["recall"] = keyword_recall(result["answer"], item["expected"])
        results.append({**item, **result})
        print(f"{result['recall']:.2f}  {item['question']}")

    summary = score(results)
    print(json.dumps(summary, indent=2))
    if summary["mean_recall"] < args.min_score:
        raise SystemExit(f"mean recall {summary['mean_recall']:.2f} below gate {args.min_score}")


if __name__ == "__main__":
    main()
