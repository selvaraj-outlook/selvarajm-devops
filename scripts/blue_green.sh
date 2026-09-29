#!/usr/bin/env bash
# Blue/green rollout of the latest registered model on a managed online endpoint.
#  1. create the endpoint on first run
#  2. deploy the new model to the idle colour
#  3. mirror nothing, send 10% live traffic, smoke test, then 100%
#  4. delete the old colour
# Usage: blue_green.sh <resource-group> <workspace> <endpoint>
set -euo pipefail
RG="$1"; WS="$2"; EP="$3"
az extension add -n ml --upgrade -y >/dev/null
az configure --defaults group="$RG" workspace="$WS"

if ! az ml online-endpoint show -n "$EP" >/dev/null 2>&1; then
  az ml online-endpoint create --file aml/endpoints/endpoint.yaml
fi

LIVE=$(az ml online-endpoint show -n "$EP" --query "traffic" -o json \
  | python3 -c "import json,sys; t=json.load(sys.stdin); print(max(t, key=t.get) if t and max(t.values())>0 else '')")
if [ "$LIVE" = "blue" ]; then NEW=green; else NEW=blue; fi
VERSION=$(az ml model list -n breast-cancer-rf --query "[0].version" -o tsv)
echo "live=${LIVE:-none} new=$NEW model=breast-cancer-rf:$VERSION"

az ml online-deployment create --file aml/endpoints/deployment.yaml --name "$NEW" \
  --set model="azureml:breast-cancer-rf:${VERSION}"

smoke() {
  az ml online-endpoint invoke -n "$EP" --deployment-name "$1" --request-file aml/endpoints/sample-request.json
}

if [ -n "$LIVE" ]; then
  smoke "$NEW"
  az ml online-endpoint update -n "$EP" --traffic "$LIVE=90 $NEW=10"
  sleep 300   # watch errors and latency in Application Insights before going further
  az ml online-endpoint update -n "$EP" --traffic "$NEW=100 $LIVE=0"
  az ml online-deployment delete -n "$LIVE" -e "$EP" --yes --no-wait
else
  az ml online-endpoint update -n "$EP" --traffic "$NEW=100"
  smoke "$NEW"
fi
echo "done: $NEW serves 100%"
