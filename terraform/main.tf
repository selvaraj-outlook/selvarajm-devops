data "aws_caller_identity" "current" {}

locals {
  account      = data.aws_caller_identity.current.account_id
  environments = toset(["staging", "production"])
}

################################################################################
# Model registry bucket and image repository
################################################################################

resource "aws_s3_bucket" "registry" {
  bucket = "${var.name}-registry-${local.account}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "registry" {
  bucket                  = aws_s3_bucket.registry.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "registry" {
  bucket = aws_s3_bucket.registry.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "registry" {
  bucket = aws_s3_bucket.registry.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_ecr_repository" "model" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_lifecycle_policy" "model" {
  repository = aws_ecr_repository.model.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the last 30 images"
      selection    = { tagStatus = "any", countType = "imageCountMoreThan", countNumber = 30 }
      action       = { type = "expire" }
    }]
  })
}

################################################################################
# GitHub OIDC: one role per GitHub environment, trusted only from that environment
################################################################################

resource "aws_iam_openid_connect_provider" "github" {
  count           = var.create_github_oidc_provider ? 1 : 0
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

locals {
  oidc_provider_arn = var.create_github_oidc_provider ? aws_iam_openid_connect_provider.github[0].arn : "arn:aws:iam::${local.account}:oidc-provider/token.actions.githubusercontent.com"
}

data "aws_iam_policy_document" "github_assume" {
  for_each = local.environments
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [local.oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repository}:environment:${each.key}"]
    }
  }
}

resource "aws_iam_role" "github" {
  for_each           = local.environments
  name               = "${var.name}-github-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.github_assume[each.key].json
}

data "aws_iam_policy_document" "github" {
  for_each = local.environments
  statement {
    sid       = "Registry"
    actions   = ["s3:ListBucket", "s3:GetObject", "s3:PutObject"]
    resources = [aws_s3_bucket.registry.arn, "${aws_s3_bucket.registry.arn}/*"]
  }
  statement {
    sid       = "EcrLogin"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }
  statement {
    sid = "EcrPush"
    actions = [
      "ecr:BatchCheckLayerAvailability", "ecr:BatchGetImage", "ecr:CompleteLayerUpload", "ecr:DescribeImages",
      "ecr:InitiateLayerUpload", "ecr:PutImage", "ecr:UploadLayerPart",
    ]
    resources = [aws_ecr_repository.model.arn]
  }
  statement {
    sid       = "DeployOwnService"
    actions   = ["apprunner:UpdateService", "apprunner:DescribeService", "apprunner:ListOperations"]
    resources = [aws_apprunner_service.model[each.key].arn]
  }
  statement {
    sid       = "PassEcrAccessRole"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.apprunner_ecr.arn]
  }
}

resource "aws_iam_role_policy" "github" {
  for_each = local.environments
  name     = "deploy"
  role     = aws_iam_role.github[each.key].id
  policy   = data.aws_iam_policy_document.github[each.key].json
}

################################################################################
# App Runner: staging and production services
################################################################################

data "aws_iam_policy_document" "apprunner_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["build.apprunner.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "apprunner_ecr" {
  name               = "${var.name}-apprunner-ecr"
  assume_role_policy = data.aws_iam_policy_document.apprunner_assume.json
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_ecr.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

resource "aws_apprunner_auto_scaling_configuration_version" "model" {
  auto_scaling_configuration_name = "${var.name}-scaling"
  min_size                        = 1
  max_size                        = 4
  max_concurrency                 = 50
}

resource "aws_apprunner_service" "model" {
  for_each     = local.environments
  service_name = "${var.name}-${each.key}"

  source_configuration {
    auto_deployments_enabled = false
    image_repository {
      image_identifier      = var.bootstrap_image
      image_repository_type = "ECR_PUBLIC"
      image_configuration {
        port = "8080"
      }
    }
  }

  instance_configuration {
    cpu    = "1024"
    memory = "2048"
  }

  health_check_configuration {
    protocol = "HTTP"
    path     = "/health"
  }

  auto_scaling_configuration_arn = aws_apprunner_auto_scaling_configuration_version.model.arn

  # The pipeline owns the running image from the first deployment on.
  lifecycle {
    ignore_changes = [source_configuration]
  }
}
