variable "region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix."
  type        = string
  default     = "credit-default"
}

variable "github_repository" {
  description = "GitHub repository allowed to deploy, as owner/name."
  type        = string
}

variable "create_github_oidc_provider" {
  description = "Create the GitHub OIDC provider (only one per account; set false if it exists)."
  type        = bool
  default     = true
}

variable "bootstrap_image" {
  description = "Image App Runner starts with before the pipeline pushes the first model image."
  type        = string
  default     = "public.ecr.aws/aws-containers/hello-app-runner:latest"
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "ml-cicd-github-actions"
    ManagedBy = "terraform"
  }
}
