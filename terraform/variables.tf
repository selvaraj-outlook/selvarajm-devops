variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster to create."
  type        = string
  default     = "kserve-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "CIDR block for the cluster VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread subnets and nodes across."
  type        = number
  default     = 3
}

variable "single_nat_gateway" {
  description = "Use one NAT gateway for all AZs (cheaper) instead of one per AZ (highly available)."
  type        = bool
  default     = true
}

variable "node_instance_types" {
  description = "Instance types for the managed node group, in any order. Use several 2 vCPU / 8 GiB types so a capacity shortage on one does not block the deploy."
  type        = list(string)
  default     = ["t3.large", "t3a.large", "m5.large", "m5a.large", "m6i.large"]
}

variable "node_capacity_type" {
  description = "ON_DEMAND or SPOT. SPOT is cheaper and draws on more capacity pools, but nodes can be reclaimed."
  type        = string
  default     = "ON_DEMAND"

  validation {
    condition     = contains(["ON_DEMAND", "SPOT"], var.node_capacity_type)
    error_message = "node_capacity_type must be ON_DEMAND or SPOT."
  }
}

variable "node_min_size" {
  type    = number
  default = 2
}

variable "node_max_size" {
  type    = number
  default = 5
}

variable "node_desired_size" {
  type    = number
  default = 2
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "CIDRs allowed to reach the public Kubernetes API endpoint. Restrict this outside of experiments."
  type        = list(string)
  default     = ["0.0.0.0/0"]
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
