#!/usr/bin/env bash
# Fill the dev overlay with real values from `terraform output`.
# Usage: scripts/render-overlay.sh <image-tag>
set -euo pipefail

TAG="${1:?usage: $0 <image-tag>}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TF="terraform -chdir=$ROOT/terraform output -raw"

REPO="$($TF ecr_repository_url)"
ROLE="$($TF irsa_role_arn)"
SECRET="$($TF db_secret_arn)"
BUCKET="$($TF artifact_bucket)"
HOST="$($TF db_endpoint | cut -d: -f1)"

cd "$ROOT/k8s/overlays/dev"
kustomize edit set image "mlflow-server=${REPO}:${TAG}"

python3 - "$ROLE" "$HOST" "$SECRET" "$BUCKET" <<'PY'
import re, sys
role, host, secret, bucket = sys.argv[1:]
path = "kustomization.yaml"
text = open(path).read()
text = re.sub(r"(role-arn\n\s+value: ).*", r"\g<1>" + role, text)
text = re.sub(r"(/data/DB_HOST\n\s+value: ).*", r"\g<1>" + host, text)
text = re.sub(r"(/data/DB_SECRET_ARN\n\s+value: ).*", r"\g<1>" + secret, text)
text = re.sub(r"(/data/ARTIFACT_BUCKET\n\s+value: ).*", r"\g<1>" + bucket, text)
open(path, "w").write(text)
PY
echo "Overlay updated. Review with: kustomize build k8s/overlays/dev"
