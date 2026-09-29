data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account         = data.aws_caller_identity.current.account_id
  collection_name = "${var.name}-vectors"
  embedding_arn   = "arn:${data.aws_partition.current.partition}:bedrock:${var.region}::foundation-model/${var.embedding_model_id}"
  generation_arn  = "arn:${data.aws_partition.current.partition}:bedrock:${var.region}::foundation-model/${var.generation_model_id}"
}

################################################################################
# Source documents
################################################################################

resource "aws_s3_bucket" "docs" {
  bucket = "${var.name}-docs-${local.account}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "docs" {
  bucket                  = aws_s3_bucket.docs.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "docs" {
  bucket = aws_s3_bucket.docs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "docs" {
  bucket = aws_s3_bucket.docs.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

################################################################################
# Vector store: OpenSearch Serverless (VECTORSEARCH collection)
################################################################################

resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.name}-enc"
  type = "encryption"
  policy = jsonencode({
    Rules       = [{ ResourceType = "collection", Resource = ["collection/${local.collection_name}"] }]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.name}-net"
  type = "network"
  policy = jsonencode([{
    Rules = [
      { ResourceType = "collection", Resource = ["collection/${local.collection_name}"] },
      { ResourceType = "dashboard", Resource = ["collection/${local.collection_name}"] },
    ]
    AllowFromPublic = true
  }])
}

resource "aws_opensearchserverless_access_policy" "data" {
  name = "${var.name}-data"
  type = "data"
  policy = jsonencode([{
    Rules = [
      {
        ResourceType = "index"
        Resource     = ["index/${local.collection_name}/*"]
        Permission   = ["aoss:CreateIndex", "aoss:DescribeIndex", "aoss:UpdateIndex", "aoss:ReadDocument", "aoss:WriteDocument"]
      },
      {
        ResourceType = "collection"
        Resource     = ["collection/${local.collection_name}"]
        Permission   = ["aoss:DescribeCollectionItems", "aoss:CreateCollectionItems", "aoss:UpdateCollectionItems"]
      },
    ]
    Principal = concat([aws_iam_role.knowledge_base.arn], var.admin_principal_arns)
  }])
}

resource "aws_opensearchserverless_collection" "vectors" {
  name             = local.collection_name
  type             = "VECTORSEARCH"
  standby_replicas = "DISABLED" # lower cost for non-production; enable for HA
  depends_on       = [aws_opensearchserverless_security_policy.encryption, aws_opensearchserverless_security_policy.network]
}

################################################################################
# Knowledge base service role
################################################################################

data "aws_iam_policy_document" "kb_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["bedrock.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [local.account]
    }
  }
}

resource "aws_iam_role" "knowledge_base" {
  name               = "${var.name}-knowledge-base"
  assume_role_policy = data.aws_iam_policy_document.kb_assume.json
}

data "aws_iam_policy_document" "knowledge_base" {
  statement {
    sid       = "Embeddings"
    actions   = ["bedrock:InvokeModel"]
    resources = [local.embedding_arn]
  }
  statement {
    sid       = "ReadDocs"
    actions   = ["s3:ListBucket", "s3:GetObject"]
    resources = [aws_s3_bucket.docs.arn, "${aws_s3_bucket.docs.arn}/*"]
  }
  statement {
    sid       = "VectorStore"
    actions   = ["aoss:APIAccessAll"]
    resources = [aws_opensearchserverless_collection.vectors.arn]
  }
}

resource "aws_iam_role_policy" "knowledge_base" {
  name   = "knowledge-base"
  role   = aws_iam_role.knowledge_base.id
  policy = data.aws_iam_policy_document.knowledge_base.json
}

################################################################################
# Knowledge base + S3 data source (phase 2, after the index exists)
################################################################################

resource "aws_bedrockagent_knowledge_base" "this" {
  count    = var.create_knowledge_base ? 1 : 0
  name     = "${var.name}-kb"
  role_arn = aws_iam_role.knowledge_base.arn

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = local.embedding_arn
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.vectors.arn
      vector_index_name = var.index_name
      field_mapping {
        vector_field   = "embedding"
        text_field     = "text"
        metadata_field = "metadata"
      }
    }
  }

  depends_on = [aws_iam_role_policy.knowledge_base, aws_opensearchserverless_access_policy.data]
}

resource "aws_bedrockagent_data_source" "docs" {
  count             = var.create_knowledge_base ? 1 : 0
  name              = "${var.name}-s3-docs"
  knowledge_base_id = aws_bedrockagent_knowledge_base.this[0].id

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.docs.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "FIXED_SIZE"
      fixed_size_chunking_configuration {
        max_tokens         = 400
        overlap_percentage = 15
      }
    }
  }
}

################################################################################
# Guardrail: block prompt attacks and redact PII in answers
################################################################################

resource "aws_bedrock_guardrail" "this" {
  name                      = "${var.name}-guardrail"
  blocked_input_messaging   = "Sorry, I can't help with that request."
  blocked_outputs_messaging = "Sorry, I can't share that answer."

  content_policy_config {
    filters_config {
      type            = "PROMPT_ATTACK"
      input_strength  = "HIGH"
      output_strength = "NONE"
    }
    filters_config {
      type            = "HATE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
    filters_config {
      type            = "VIOLENCE"
      input_strength  = "HIGH"
      output_strength = "HIGH"
    }
  }

  sensitive_information_policy_config {
    pii_entities_config {
      type   = "EMAIL"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "PHONE"
      action = "ANONYMIZE"
    }
    pii_entities_config {
      type   = "CREDIT_DEBIT_CARD_NUMBER"
      action = "BLOCK"
    }
  }
}

resource "aws_bedrock_guardrail_version" "this" {
  guardrail_arn = aws_bedrock_guardrail.this.guardrail_arn
  description   = "Managed by Terraform"
}
