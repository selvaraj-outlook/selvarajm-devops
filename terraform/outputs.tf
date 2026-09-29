output "docs_bucket" {
  description = "Upload source documents here."
  value       = aws_s3_bucket.docs.bucket
}

output "collection_endpoint" {
  description = "OpenSearch Serverless endpoint (used by scripts/create_index.py)."
  value       = aws_opensearchserverless_collection.vectors.collection_endpoint
}

output "knowledge_base_id" {
  description = "Bedrock knowledge base ID."
  value       = try(aws_bedrockagent_knowledge_base.this[0].id, null)
}

output "data_source_id" {
  description = "S3 data source ID."
  value       = try(aws_bedrockagent_data_source.docs[0].data_source_id, null)
}

output "rag_api_url" {
  description = "IAM-authenticated function URL for the RAG API."
  value       = try(aws_lambda_function_url.rag_api[0].function_url, null)
}

output "guardrail_id" {
  description = "Bedrock guardrail ID."
  value       = aws_bedrock_guardrail.this.guardrail_id
}
