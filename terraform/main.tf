data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
}

################################################################################
# Data, code and artifact bucket
################################################################################

resource "aws_s3_bucket" "ml" {
  bucket = "${var.name}-sagemaker-${local.account}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "ml" {
  bucket                  = aws_s3_bucket.ml.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "ml" {
  bucket = aws_s3_bucket.ml.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "ml" {
  bucket = aws_s3_bucket.ml.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "ml" {
  bucket = aws_s3_bucket.ml.id
  rule {
    id     = "expire-pipeline-runs"
    status = "Enabled"
    filter {
      prefix = "runs/"
    }
    expiration {
      days = 60
    }
  }
}

################################################################################
# SageMaker execution role (pipeline steps and the endpoint)
################################################################################

data "aws_iam_policy_document" "sagemaker_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["sagemaker.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sagemaker" {
  name               = "${var.name}-sagemaker-execution"
  assume_role_policy = data.aws_iam_policy_document.sagemaker_assume.json
}

data "aws_iam_policy_document" "sagemaker" {
  statement {
    sid       = "Bucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.ml.arn]
  }
  statement {
    sid       = "Objects"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.ml.arn}/*"]
  }
  statement {
    sid = "SageMakerJobs"
    actions = [
      "sagemaker:CreateProcessingJob", "sagemaker:DescribeProcessingJob", "sagemaker:StopProcessingJob",
      "sagemaker:CreateTrainingJob", "sagemaker:DescribeTrainingJob", "sagemaker:StopTrainingJob",
      "sagemaker:CreateModelPackage", "sagemaker:DescribeModelPackage",
      "sagemaker:AddTags", "sagemaker:CreateExperiment", "sagemaker:CreateTrial",
      "sagemaker:AssociateTrialComponent", "sagemaker:DescribeExperiment", "sagemaker:DescribeTrial",
    ]
    resources = ["*"]
  }
  statement {
    sid       = "PassSelf"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.sagemaker.arn]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["sagemaker.amazonaws.com"]
    }
  }
  statement {
    sid       = "PullFrameworkImages"
    actions   = ["ecr:GetAuthorizationToken", "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer", "ecr:BatchCheckLayerAvailability"]
    resources = ["*"]
  }
  statement {
    sid       = "Logs"
    actions   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents", "logs:DescribeLogStreams", "cloudwatch:PutMetricData"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sagemaker" {
  name   = "pipeline-execution"
  role   = aws_iam_role.sagemaker.id
  policy = data.aws_iam_policy_document.sagemaker.json
}

################################################################################
# Model registry
################################################################################

resource "aws_sagemaker_model_package_group" "this" {
  model_package_group_name        = "${var.name}-models"
  model_package_group_description = "Models registered by the ${var.name} training pipeline"
}

################################################################################
# Deployer: EventBridge (package Approved) -> Lambda -> endpoint
################################################################################

data "archive_file" "deployer" {
  type        = "zip"
  source_dir  = "${path.module}/../lambda/deployer"
  output_path = "${path.module}/.build/deployer.zip"
}

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "deployer" {
  name               = "${var.name}-model-deployer"
  assume_role_policy = data.aws_iam_policy_document.lambda_assume.json
}

data "aws_iam_policy_document" "deployer" {
  statement {
    actions = [
      "sagemaker:CreateModel", "sagemaker:CreateEndpointConfig", "sagemaker:CreateEndpoint",
      "sagemaker:UpdateEndpoint", "sagemaker:DescribeEndpoint", "sagemaker:DescribeModelPackage",
    ]
    resources = ["*"]
  }
  statement {
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.sagemaker.arn]
  }
  statement {
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.deployer.arn}:*"]
  }
}

resource "aws_iam_role_policy" "deployer" {
  name   = "deploy-endpoint"
  role   = aws_iam_role.deployer.id
  policy = data.aws_iam_policy_document.deployer.json
}

resource "aws_cloudwatch_log_group" "deployer" {
  name              = "/aws/lambda/${var.name}-model-deployer"
  retention_in_days = 30
}

resource "aws_lambda_function" "deployer" {
  function_name    = "${var.name}-model-deployer"
  role             = aws_iam_role.deployer.arn
  runtime          = "python3.12"
  handler          = "handler.handler"
  filename         = data.archive_file.deployer.output_path
  source_code_hash = data.archive_file.deployer.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      ENDPOINT_NAME      = var.name
      EXECUTION_ROLE_ARN = aws_iam_role.sagemaker.arn
      INSTANCE_TYPE      = var.endpoint_instance_type
      INSTANCE_COUNT     = tostring(var.endpoint_instance_count)
    }
  }

  depends_on = [aws_cloudwatch_log_group.deployer]
}

resource "aws_cloudwatch_event_rule" "approved" {
  name        = "${var.name}-model-approved"
  description = "Model package approved in ${aws_sagemaker_model_package_group.this.model_package_group_name}"
  event_pattern = jsonencode({
    source      = ["aws.sagemaker"]
    detail-type = ["SageMaker Model Package State Change"]
    detail = {
      ModelPackageGroupName = [aws_sagemaker_model_package_group.this.model_package_group_name]
      ModelApprovalStatus   = ["Approved"]
    }
  })
}

resource "aws_cloudwatch_event_target" "deployer" {
  rule = aws_cloudwatch_event_rule.approved.name
  arn  = aws_lambda_function.deployer.arn
}

resource "aws_lambda_permission" "events" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.deployer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.approved.arn
}
