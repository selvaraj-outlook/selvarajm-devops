output "model_bucket" {
  description = "Bucket that approved models are published to."
  value       = aws_s3_bucket.models.bucket
}

output "runner_role_arn" {
  description = "IRSA role to annotate on the pipeline-runner service account."
  value       = aws_iam_role.runner.arn
}
