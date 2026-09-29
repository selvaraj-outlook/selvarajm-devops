output "artifact_bucket" {
  description = "S3 bucket holding MLflow artifacts."
  value       = aws_s3_bucket.artifacts.bucket
}

output "db_endpoint" {
  description = "RDS endpoint (host:port) for the backend store."
  value       = aws_db_instance.this.endpoint
}

output "db_secret_arn" {
  description = "Secrets Manager ARN holding the RDS master credentials."
  value       = aws_db_instance.this.master_user_secret[0].secret_arn
}

output "irsa_role_arn" {
  description = "IAM role to annotate on the mlflow service account."
  value       = aws_iam_role.mlflow.arn
}

output "ecr_repository_url" {
  description = "ECR repository for the MLflow server image."
  value       = aws_ecr_repository.mlflow.repository_url
}
