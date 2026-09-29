variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "EKS cluster for the monitoring stack and drift job."
  type        = string
}

variable "name" {
  description = "Name prefix."
  type        = string
  default     = "drift"
}

variable "install_monitoring_stack" {
  description = "Install kube-prometheus-stack. Set false if Prometheus/Grafana already run in the cluster."
  type        = bool
  default     = true
}

variable "kube_prometheus_stack_version" {
  description = "kube-prometheus-stack chart version."
  type        = string
  default     = "66.2.1"
}

variable "pushgateway_version" {
  description = "prometheus-pushgateway chart version."
  type        = string
  default     = "2.15.0"
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "model-drift-monitoring"
    ManagedBy = "terraform"
  }
}
