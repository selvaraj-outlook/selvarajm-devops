data "aws_caller_identity" "current" {}

data "aws_eks_cluster" "this" {
  name = var.cluster_name
}

locals {
  account     = data.aws_caller_identity.current.account_id
  oidc_issuer = replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")
}

################################################################################
# S3: offline feature data (parquet) and the Feast registry
################################################################################

resource "aws_s3_bucket" "feast" {
  bucket = "${var.name}-${local.account}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "feast" {
  bucket                  = aws_s3_bucket.feast.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "feast" {
  bucket = aws_s3_bucket.feast.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "feast" {
  bucket = aws_s3_bucket.feast.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

################################################################################
# Least-privilege policy for Feast: registry + data in S3, its own DynamoDB tables
################################################################################

data "aws_iam_policy_document" "feast" {
  statement {
    sid       = "ListBucket"
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.feast.arn]
  }
  statement {
    sid       = "ReadData"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.feast.arn}/data/*"]
  }
  statement {
    sid       = "Registry"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.feast.arn}/registry/*"]
  }
  statement {
    sid = "OnlineStore"
    actions = [
      "dynamodb:CreateTable", "dynamodb:DescribeTable", "dynamodb:DeleteTable",
      "dynamodb:BatchWriteItem", "dynamodb:BatchGetItem", "dynamodb:GetItem",
      "dynamodb:PutItem", "dynamodb:Query", "dynamodb:TagResource",
    ]
    resources = ["arn:aws:dynamodb:${var.region}:${local.account}:table/${var.feast_project}.*"]
  }
}

resource "aws_iam_policy" "feast" {
  name   = "${var.name}-feature-store"
  policy = data.aws_iam_policy_document.feast.json
}

################################################################################
# IRSA role for the materialization CronJob
################################################################################

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${local.account}:oidc-provider/${local.oidc_issuer}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:sub"
      values   = ["system:serviceaccount:${var.namespace}:${var.service_account}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "materialize" {
  name               = "${var.name}-materialize"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

resource "aws_iam_role_policy_attachment" "materialize" {
  role       = aws_iam_role.materialize.name
  policy_arn = aws_iam_policy.feast.arn
}

resource "aws_ecr_repository" "feast" {
  name                 = "${var.name}/materialize"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}
