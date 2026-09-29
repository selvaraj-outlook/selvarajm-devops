variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Existing EKS cluster (1.29+, API or API_AND_CONFIG_MAP authentication mode)."
  type        = string
}

variable "karpenter_version" {
  description = "Karpenter Helm chart version."
  type        = string
  default     = "1.1.1"
}

variable "keda_version" {
  description = "KEDA Helm chart version."
  type        = string
  default     = "2.16.0"
}

variable "karpenter_namespace" {
  description = "Namespace for the Karpenter controller."
  type        = string
  default     = "kube-system"
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "karpenter-gpu-autoscaling"
    ManagedBy = "terraform"
  }
}
