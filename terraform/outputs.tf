output "bucket" {
  description = "Bucket for offline data (data/) and the registry (registry/)."
  value       = aws_s3_bucket.feast.bucket
}

output "feast_policy_arn" {
  description = "Attach to any role that runs Feast (CI, notebooks, services)."
  value       = aws_iam_policy.feast.arn
}

output "materialize_role_arn" {
  description = "IRSA role for the materialization CronJob."
  value       = aws_iam_role.materialize.arn
}

output "ecr_repository_url" {
  description = "Image repository for the Feast job image."
  value       = aws_ecr_repository.feast.repository_url
}
