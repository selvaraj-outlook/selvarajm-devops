variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix; also the pipeline and endpoint name."
  type        = string
  default     = "churn"
}

variable "endpoint_instance_type" {
  description = "Instance type for the real-time endpoint."
  type        = string
  default     = "ml.m5.large"
}

variable "endpoint_instance_count" {
  description = "Instance count for the real-time endpoint."
  type        = number
  default     = 1
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "sagemaker-pipelines"
    ManagedBy = "terraform"
  }
}
