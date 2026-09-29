data "aws_caller_identity" "current" {}

locals {
  oidc_issuer = replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")
}

################################################################################
# Model store: versioned S3 bucket, one prefix per model version
################################################################################

resource "aws_s3_bucket" "models" {
  bucket = "${var.name}-models-${data.aws_caller_identity.current.account_id}-${var.region}"
}

resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

################################################################################
# IRSA: predictors get read-only access to the model bucket
################################################################################

data "aws_iam_policy_document" "assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/${local.oidc_issuer}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:sub"
      values   = ["system:serviceaccount:${var.model_namespace}:${var.model_service_account}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "model_puller" {
  name               = "${var.name}-model-puller"
  assume_role_policy = data.aws_iam_policy_document.assume.json
}

data "aws_iam_policy_document" "read_models" {
  statement {
    actions   = ["s3:ListBucket"]
    resources = [aws_s3_bucket.models.arn]
  }
  statement {
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.models.arn}/*"]
  }
}

resource "aws_iam_role_policy" "read_models" {
  name   = "read-models"
  role   = aws_iam_role.model_puller.id
  policy = data.aws_iam_policy_document.read_models.json
}

################################################################################
# Platform: cert-manager -> Knative operator -> KServe (Serverless mode)
################################################################################

resource "helm_release" "cert_manager" {
  name             = "cert-manager"
  repository       = "https://charts.jetstack.io"
  chart            = "cert-manager"
  version          = var.cert_manager_version
  namespace        = "cert-manager"
  create_namespace = true
  wait             = true

  set {
    name  = "crds.enabled"
    value = "true"
  }
}

resource "helm_release" "knative_operator" {
  name             = "knative-operator"
  repository       = "https://knative.github.io/operator"
  chart            = "knative-operator"
  version          = var.knative_operator_version
  namespace        = "knative-operator"
  create_namespace = true
  wait             = true
}

resource "helm_release" "kserve_crd" {
  name             = "kserve-crd"
  repository       = "oci://ghcr.io/kserve/charts"
  chart            = "kserve-crd"
  version          = var.kserve_version
  namespace        = "kserve"
  create_namespace = true
}

resource "helm_release" "kserve" {
  name       = "kserve"
  repository = "oci://ghcr.io/kserve/charts"
  chart      = "kserve"
  version    = var.kserve_version
  namespace  = "kserve"
  wait       = true

  # Knative + Kourier instead of Istio keeps the footprint small.
  values = [yamlencode({
    kserve = {
      controller = {
        deploymentMode = "Serverless"
        gateway = {
          disableIstioVirtualHost = true
        }
      }
    }
  })]

  depends_on = [helm_release.cert_manager, helm_release.kserve_crd, helm_release.knative_operator]
}
