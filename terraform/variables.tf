variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-west-2"
}

variable "cluster_name" {
  description = "Name of the EKS cluster to create."
  type        = string
  default     = "code-eks"
}

variable "kubernetes_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.30"
}

variable "vpc_id" {
  description = "Existing VPC to deploy the cluster into."
  type        = string
  default     = "vpc-06348d507b3dec089"
}

variable "subnet_ids" {
  description = "Private subnets for the cluster and nodes."
  type        = list(string)
  default = [
    "subnet-07178b972c79ead3d", # project-subnet-private1-us-west-2b
    "subnet-08d446be8309a9b0d", # project-subnet-private2-us-west-2a
  ]
}

variable "nat_public_subnet_id" {
  description = "Public subnet that hosts the NAT gateway."
  type        = string
  default     = "subnet-00b0a1297e4d00bea" # project-subnet-public2-us-west-2a
}

variable "node_instance_types" {
  description = "Instance types for the managed node group."
  type        = list(string)
  default     = ["t3.medium"]
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
