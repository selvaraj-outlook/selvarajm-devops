variable "region" {
  description = "AWS region to deploy into."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix for every resource."
  type        = string
  default     = "mlflow"
}

variable "cluster_name" {
  description = "Existing EKS cluster that will run the MLflow server."
  type        = string
}

variable "vpc_id" {
  description = "VPC of the EKS cluster."
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnets for the RDS instance (at least two AZs)."
  type        = list(string)
}

variable "namespace" {
  description = "Kubernetes namespace for MLflow."
  type        = string
  default     = "mlflow"
}

variable "service_account" {
  description = "Kubernetes service account used by the MLflow server (IRSA)."
  type        = string
  default     = "mlflow"
}

variable "db_instance_class" {
  description = "RDS instance class for the MLflow backend store."
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS storage in GiB."
  type        = number
  default     = 20
}

variable "artifact_retention_days" {
  description = "Days before noncurrent artifact versions are expired."
  type        = number
  default     = 90
}

variable "deletion_protection" {
  description = "Protect the database from accidental deletion. Set false for throwaway environments."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags applied to every resource."
  type        = map(string)
  default = {
    Project   = "mlflow-on-eks"
    ManagedBy = "terraform"
  }
}
