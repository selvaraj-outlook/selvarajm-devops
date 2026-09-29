variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Existing EKS cluster to install KServe into."
  type        = string
}

variable "name" {
  description = "Name prefix for AWS resources."
  type        = string
  default     = "kserve"
}

variable "model_namespace" {
  description = "Namespace where InferenceServices run."
  type        = string
  default     = "models"
}

variable "model_service_account" {
  description = "Service account used by predictors to pull models from S3."
  type        = string
  default     = "model-puller"
}

variable "cert_manager_version" {
  description = "cert-manager Helm chart version."
  type        = string
  default     = "v1.16.2"
}

variable "knative_operator_version" {
  description = "Knative operator Helm chart version."
  type        = string
  default     = "v1.16.0"
}

variable "kserve_version" {
  description = "KServe Helm chart version."
  type        = string
  default     = "v0.14.1"
}

variable "tags" {
  description = "Tags for AWS resources."
  type        = map(string)
  default = {
    Project   = "kserve-model-serving"
    ManagedBy = "terraform"
  }
}
