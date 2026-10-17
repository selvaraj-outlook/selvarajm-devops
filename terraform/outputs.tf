output "model_bucket" {
  description = "Bucket where model versions are published."
  value       = aws_s3_bucket.models.bucket
}

output "model_puller_role_arn" {
  description = "IRSA role for the predictor service account."
  value       = aws_iam_role.model_puller.arn
}

output "cluster_name" {
  description = "Name of the EKS cluster."
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "Kubernetes API endpoint."
  value       = module.eks.cluster_endpoint
}

output "vpc_id" {
  description = "VPC hosting the cluster."
  value       = var.vpc_id
}

output "update_kubeconfig" {
  description = "Command that configures kubectl for the cluster."
  value       = "aws eks update-kubeconfig --name ${module.eks.cluster_name} --region ${var.region}"
}

output "model_publisher_role_arn" {
  description = "IRSA role for the publish Job."
  value       = aws_iam_role.model_publisher.arn
}
