output "model_bucket" {
  description = "Bucket where model versions are published."
  value       = aws_s3_bucket.models.bucket
}

output "model_puller_role_arn" {
  description = "IRSA role for the predictor service account."
  value       = aws_iam_role.model_puller.arn
}
