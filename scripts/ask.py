"""Call the IAM-authenticated RAG function URL with SigV4.

python scripts/ask.py --url <rag_api_url> "How many days of leave do I get?"
"""

from __future__ import annotations

import argparse
import json
import urllib.request

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("question")
    args = parser.parse_args()

    body = json.dumps({"question": args.question})
    request = AWSRequest(method="POST", url=args.url, data=body, headers={"content-type": "application/json"})
    SigV4Auth(boto3.Session().get_credentials(), "lambda", args.region).add_auth(request)
    prepared = urllib.request.Request(args.url, data=body.encode(), headers=dict(request.headers), method="POST")
    with urllib.request.urlopen(prepared, timeout=60) as response:  # noqa: S310 - URL comes from Terraform output
        print(json.dumps(json.loads(response.read()), indent=2))


if __name__ == "__main__":
    main()
