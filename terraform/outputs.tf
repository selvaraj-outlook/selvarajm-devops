output "registry_bucket" {
  description = "S3 model registry."
  value       = aws_s3_bucket.registry.bucket
}

output "ecr_repository_url" {
  description = "Model server images."
  value       = aws_ecr_repository.model.repository_url
}

output "github_role_arns" {
  description = "Set as AWS_ROLE_ARN in the matching GitHub environment."
  value       = { for env, role in aws_iam_role.github : env => role.arn }
}

output "service_arns" {
  description = "App Runner service ARNs per environment."
  value       = { for env, svc in aws_apprunner_service.model : env => svc.arn }
}

output "service_urls" {
  description = "App Runner URLs per environment."
  value       = { for env, svc in aws_apprunner_service.model : env => "https://${svc.service_url}" }
}

output "apprunner_ecr_role_arn" {
  description = "Role App Runner uses to pull from ECR."
  value       = aws_iam_role.apprunner_ecr.arn
}
