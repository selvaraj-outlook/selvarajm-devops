output "bucket" {
  description = "Bucket for data, code and pipeline outputs."
  value       = aws_s3_bucket.ml.bucket
}

output "execution_role_arn" {
  description = "SageMaker execution role for pipeline steps and endpoints."
  value       = aws_iam_role.sagemaker.arn
}

output "model_package_group" {
  description = "Model registry group."
  value       = aws_sagemaker_model_package_group.this.model_package_group_name
}

output "endpoint_name" {
  description = "Endpoint that approved models are deployed to."
  value       = var.name
}
