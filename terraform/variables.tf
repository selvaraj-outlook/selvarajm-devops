variable "region" {
  description = "AWS region with Bedrock Knowledge Bases available."
  type        = string
  default     = "us-east-1"
}

variable "name" {
  description = "Name prefix (lowercase, max 20 characters because of OpenSearch Serverless limits)."
  type        = string
  default     = "rag"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{1,19}$", var.name))
    error_message = "name must be lowercase alphanumeric/hyphen, 2-20 characters."
  }
}

variable "embedding_model_id" {
  description = "Bedrock embedding model."
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "embedding_dimensions" {
  description = "Vector size produced by the embedding model."
  type        = number
  default     = 1024
}

variable "generation_model_id" {
  description = "Bedrock model used to generate answers."
  type        = string
  default     = "anthropic.claude-3-5-sonnet-20240620-v1:0"
}

variable "index_name" {
  description = "Vector index inside the collection (created by scripts/create_index.py)."
  type        = string
  default     = "bedrock-kb-index"
}

variable "create_knowledge_base" {
  description = "Second phase: set true after the vector index exists (see README)."
  type        = bool
  default     = false
}

variable "admin_principal_arns" {
  description = "IAM principals allowed to manage the vector index (the role you run create_index.py with)."
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags for every resource."
  type        = map(string)
  default = {
    Project   = "bedrock-rag-platform"
    ManagedBy = "terraform"
  }
}
