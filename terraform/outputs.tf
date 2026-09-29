output "data_bucket" {
  description = "Bucket for reference/ and inference/ data."
  value       = aws_s3_bucket.data.bucket
}

output "drift_role_arn" {
  description = "IRSA role for the model-drift service account."
  value       = aws_iam_role.drift.arn
}

output "ecr_repository_url" {
  description = "Image repository for the drift job."
  value       = aws_ecr_repository.drift.repository_url
}
