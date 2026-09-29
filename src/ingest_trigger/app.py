"""Start a knowledge-base ingestion job when documents change in S3.

Only one ingestion job can run per data source; if one is already running
the ConflictException is logged and ignored because that job (or the next
upload) will pick up the change.
"""

from __future__ import annotations

import os

import boto3

client = boto3.client("bedrock-agent")


def handler(event, _context, bedrock=None):
    bedrock = bedrock or client
    keys = [r["s3"]["object"]["key"] for r in event.get("Records", [])]
    try:
        job = bedrock.start_ingestion_job(
            knowledgeBaseId=os.environ["KNOWLEDGE_BASE_ID"],
            dataSourceId=os.environ["DATA_SOURCE_ID"],
            description=f"Triggered by {len(keys)} S3 change(s)",
        )["ingestionJob"]
        return {"started": job["ingestionJobId"], "keys": keys}
    except bedrock.exceptions.ConflictException:
        return {"skipped": "ingestion already running", "keys": keys}
