variable "location" {
  description = "Azure region."
  type        = string
  default     = "centralindia"
}

variable "name" {
  description = "Short name prefix (lowercase letters and digits)."
  type        = string
  default     = "mlops"
  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.name))
    error_message = "name must be 3-12 lowercase letters/digits (storage and registry names are derived from it)."
  }
}

variable "environment" {
  description = "Environment suffix, e.g. dev or prod."
  type        = string
  default     = "dev"
}

variable "cpu_cluster_vm_size" {
  description = "VM size of the training cluster."
  type        = string
  default     = "Standard_DS3_v2"
}

variable "cpu_cluster_max_nodes" {
  description = "Maximum nodes of the training cluster (it scales to zero when idle)."
  type        = number
  default     = 4
}

variable "cpu_cluster_priority" {
  description = "Dedicated or LowPriority (cheaper, can be pre-empted)."
  type        = string
  default     = "LowPriority"
}

variable "public_network_access" {
  description = "Allow public access to the workspace. Set false and add private endpoints for production."
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    project   = "azureml-mlops"
    managedBy = "terraform"
  }
}
