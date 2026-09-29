################################################################################
# RAG API (Lambda function URL, IAM-authenticated) and ingestion trigger
################################################################################

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

data "archive_file" "rag_api" {
  type        = "zip"
  source_dir  = "${path.module}/../src/rag_api"
  output_path = "${path.module}/.build/rag_api.zip"
}

data "archive_file" "ingest_trigger" {
  type        = "zip"
  source_dir  = "${path.module}/../src/ingest_trigger"
  output_path = "${path.module}/.build/ingest_trigger.zip"
}

resource "aws_iam_role" "rag_api" {
  count              = var.create_knowledge_base ? 1 : 0
  name               = "${var.name}-rag-api"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "rag_api" {
  count = var.create_knowledge_base ? 1 : 0
  statement {
    actions   = ["bedrock:Retrieve"]
    resources = [aws_bedrockagent_knowledge_base.this[0].arn]
  }
  statement {
    # RetrieveAndGenerate has no resource-level permissions.
    actions   = ["bedrock:RetrieveAndGenerate"]
    resources = ["*"]
  }
  statement {
    actions   = ["bedrock:InvokeModel"]
    resources = [local.generation_arn]
  }
  statement {
    actions   = ["bedrock:ApplyGuardrail"]
    resources = [aws_bedrock_guardrail.this.guardrail_arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${var.name}-*:*"]
  }
}

resource "aws_iam_role_policy" "rag_api" {
  count  = var.create_knowledge_base ? 1 : 0
  name   = "rag-api"
  role   = aws_iam_role.rag_api[0].id
  policy = data.aws_iam_policy_document.rag_api[0].json
}

resource "aws_cloudwatch_log_group" "rag_api" {
  count             = var.create_knowledge_base ? 1 : 0
  name              = "/aws/lambda/${var.name}-rag-api"
  retention_in_days = 30
}

resource "aws_lambda_function" "rag_api" {
  count            = var.create_knowledge_base ? 1 : 0
  function_name    = "${var.name}-rag-api"
  role             = aws_iam_role.rag_api[0].arn
  runtime          = "python3.12"
  handler          = "app.handler"
  filename         = data.archive_file.rag_api.output_path
  source_code_hash = data.archive_file.rag_api.output_base64sha256
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.this[0].id
      MODEL_ARN         = local.generation_arn
      GUARDRAIL_ID      = aws_bedrock_guardrail.this.guardrail_id
      GUARDRAIL_VERSION = aws_bedrock_guardrail_version.this.version
      TOP_K             = "5"
    }
  }

  depends_on = [aws_cloudwatch_log_group.rag_api]
}

resource "aws_lambda_function_url" "rag_api" {
  count              = var.create_knowledge_base ? 1 : 0
  function_name      = aws_lambda_function.rag_api[0].function_name
  authorization_type = "AWS_IAM"
}

resource "aws_iam_role" "ingest_trigger" {
  count              = var.create_knowledge_base ? 1 : 0
  name               = "${var.name}-ingest-trigger"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "ingest_trigger" {
  count = var.create_knowledge_base ? 1 : 0
  statement {
    actions   = ["bedrock:StartIngestionJob"]
    resources = [aws_bedrockagent_knowledge_base.this[0].arn]
  }
  statement {
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["arn:aws:logs:${var.region}:${local.account}:log-group:/aws/lambda/${var.name}-*:*"]
  }
}

resource "aws_iam_role_policy" "ingest_trigger" {
  count  = var.create_knowledge_base ? 1 : 0
  name   = "ingest-trigger"
  role   = aws_iam_role.ingest_trigger[0].id
  policy = data.aws_iam_policy_document.ingest_trigger[0].json
}

resource "aws_lambda_function" "ingest_trigger" {
  count            = var.create_knowledge_base ? 1 : 0
  function_name    = "${var.name}-ingest-trigger"
  role             = aws_iam_role.ingest_trigger[0].arn
  runtime          = "python3.12"
  handler          = "app.handler"
  filename         = data.archive_file.ingest_trigger.output_path
  source_code_hash = data.archive_file.ingest_trigger.output_base64sha256
  timeout          = 30

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.this[0].id
      DATA_SOURCE_ID    = aws_bedrockagent_data_source.docs[0].data_source_id
    }
  }
}

resource "aws_lambda_permission" "s3" {
  count         = var.create_knowledge_base ? 1 : 0
  statement_id  = "AllowS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ingest_trigger[0].function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.docs.arn
}

resource "aws_s3_bucket_notification" "docs" {
  count  = var.create_knowledge_base ? 1 : 0
  bucket = aws_s3_bucket.docs.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.ingest_trigger[0].arn
    events              = ["s3:ObjectCreated:*", "s3:ObjectRemoved:*"]
  }

  depends_on = [aws_lambda_permission.s3]
}
