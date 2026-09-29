"""Create the k-NN vector index that the Bedrock knowledge base writes to.

Run once between the two Terraform phases, as a principal listed in
`admin_principal_arns`:

    python scripts/create_index.py --endpoint "$(terraform -chdir=terraform output -raw collection_endpoint)"
"""

from __future__ import annotations

import argparse
import time

import boto3
from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection


def index_body(dimensions: int) -> dict:
    return {
        "settings": {"index": {"knn": True, "knn.algo_param.ef_search": 512}},
        "mappings": {
            "properties": {
                "embedding": {
                    "type": "knn_vector",
                    "dimension": dimensions,
                    "method": {"name": "hnsw", "engine": "faiss", "space_type": "l2"},
                },
                "text": {"type": "text"},
                "metadata": {"type": "text", "index": False},
            }
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--endpoint", required=True, help="https://<id>.<region>.aoss.amazonaws.com")
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--index", default="bedrock-kb-index")
    parser.add_argument("--dimensions", type=int, default=1024)
    args = parser.parse_args()

    auth = AWSV4SignerAuth(boto3.Session().get_credentials(), args.region, "aoss")
    client = OpenSearch(
        hosts=[{"host": args.endpoint.removeprefix("https://"), "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=60,
    )
    if client.indices.exists(index=args.index):
        print(f"index {args.index} already exists")
        return
    client.indices.create(index=args.index, body=index_body(args.dimensions))
    time.sleep(30)  # data-access policy and index creation take a moment to propagate
    print(f"created index {args.index}")


if __name__ == "__main__":
    main()
