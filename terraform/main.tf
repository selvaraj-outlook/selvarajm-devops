data "aws_caller_identity" "current" {}

locals {
  account     = data.aws_caller_identity.current.account_id
  oidc_issuer = replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")
}

################################################################################
# Inference-log bucket: reference/ (training snapshot) and inference/date=YYYY-MM-DD/
################################################################################

resource "aws_s3_bucket" "data" {
  bucket = "${var.name}-data-${local.account}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "data" {
  bucket                  = aws_s3_bucket.data.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "data" {
  bucket = aws_s3_bucket.data.id
  rule {
    id     = "expire-inference-logs"
    status = "Enabled"
    filter {
      prefix = "inference/"
    }
    expiration {
      days = 90
    }
  }
}

################################################################################
# IRSA: the drift job reads the bucket
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
      values   = ["system:serviceaccount:monitoring:model-drift"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "drift" {
  name               = "${var.name}-job"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "drift" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.data.arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.data.arn}/*"]
  }
}

resource "aws_iam_role_policy" "drift" {
  name   = "read-data"
  role   = aws_iam_role.drift.id
  policy = data.aws_iam_policy_document.drift.json
}

resource "aws_ecr_repository" "drift" {
  name                 = "${var.name}/job"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

################################################################################
# Monitoring stack
################################################################################

resource "helm_release" "kube_prometheus_stack" {
  count            = var.install_monitoring_stack ? 1 : 0
  name             = "kube-prometheus-stack"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "kube-prometheus-stack"
  version          = var.kube_prometheus_stack_version
  namespace        = "monitoring"
  create_namespace = true

  values = [yamlencode({
    prometheus = {
      prometheusSpec = {
        # Pick up PrometheusRules and ServiceMonitors from every namespace, not only this release's.
        ruleSelectorNilUsesHelmValues           = false
        serviceMonitorSelectorNilUsesHelmValues = false
        retention                               = "15d"
      }
    }
    grafana = {
      sidecar = {
        dashboards = { enabled = true, label = "grafana_dashboard", searchNamespace = "ALL" }
      }
    }
  })]
}

resource "helm_release" "pushgateway" {
  name             = "prometheus-pushgateway"
  repository       = "https://prometheus-community.github.io/helm-charts"
  chart            = "prometheus-pushgateway"
  version          = var.pushgateway_version
  namespace        = "monitoring"
  create_namespace = true

  values = [yamlencode({
    serviceMonitor = { enabled = true }
  })]

  depends_on = [helm_release.kube_prometheus_stack]
}
