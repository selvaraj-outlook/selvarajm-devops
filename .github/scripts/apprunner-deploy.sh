#!/usr/bin/env bash
# Point an App Runner service at a new ECR image and wait for the deployment.
# Usage: apprunner-deploy.sh <service-arn> <image-uri> <ecr-access-role-arn>
set -euo pipefail
SERVICE_ARN="$1"; IMAGE="$2"; ACCESS_ROLE="$3"

aws apprunner update-service --service-arn "$SERVICE_ARN" --source-configuration "$(cat <<JSON
{
  "AutoDeploymentsEnabled": false,
  "AuthenticationConfiguration": {"AccessRoleArn": "${ACCESS_ROLE}"},
  "ImageRepository": {
    "ImageIdentifier": "${IMAGE}",
    "ImageRepositoryType": "ECR",
    "ImageConfiguration": {"Port": "8080"}
  }
}
JSON
)" >/dev/null

sleep 10  # let the update operation start before polling
for _ in $(seq 1 60); do
  STATUS=$(aws apprunner describe-service --service-arn "$SERVICE_ARN" --query 'Service.Status' --output text)
  echo "status: $STATUS"
  case "$STATUS" in
    RUNNING) exit 0 ;;
    OPERATION_IN_PROGRESS) sleep 15 ;;
    *) echo "deployment failed: $STATUS" >&2; exit 1 ;;
  esac
done
echo "timed out waiting for deployment" >&2; exit 1
