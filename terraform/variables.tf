variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster that runs the materialization CronJob."
  type        = string
}

variable "name" {
  description = "Name prefix."
  type        = string
  default     = "feast"
}

variable "feast_project" {
  description = "Feast project name (prefix of the DynamoDB tables Feast creates)."
  type        = string
  default     = "driver_stats"
}

variable "namespace" {
  description = "Kubernetes namespace of the materialization job."
  type        = string
  default     = "feast"
}

variable "service_account" {
  description = "Service account of the materialization job."
  type        = string
  default     = "feast-materialize"
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "feast-feature-store"
    ManagedBy = "terraform"
  }
}
