#!/usr/bin/env bash
# Promote or roll back the canary revision of an InferenceService.
#   scripts/promote.sh promote   -> 100% to the latest revision
#   scripts/promote.sh rollback  -> 0% to the latest revision (previous stays live)
set -euo pipefail
ACTION="${1:?usage: $0 promote|rollback}"
NS="${NAMESPACE:-models}"
ISVC="${ISVC:-wine-classifier}"

case "$ACTION" in
  promote)  PCT=100 ;;
  rollback) PCT=0 ;;
  *) echo "unknown action: $ACTION" >&2; exit 1 ;;
esac

kubectl -n "$NS" patch inferenceservice "$ISVC" --type merge \
  -p "{\"spec\":{\"predictor\":{\"canaryTrafficPercent\":${PCT}}}}"
kubectl -n "$NS" wait --for=condition=Ready "inferenceservice/$ISVC" --timeout=5m
kubectl -n "$NS" get inferenceservice "$ISVC"
