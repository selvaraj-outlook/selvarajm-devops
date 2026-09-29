variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster running Kubeflow Pipelines."
  type        = string
}

variable "name" {
  description = "Name prefix."
  type        = string
  default     = "kfp"
}

variable "kfp_namespace" {
  description = "Namespace of Kubeflow Pipelines."
  type        = string
  default     = "kubeflow"
}

variable "runner_service_account" {
  description = "Service account that pipeline pods run as."
  type        = string
  default     = "pipeline-runner"
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "kubeflow-training-pipeline"
    ManagedBy = "terraform"
  }
}
