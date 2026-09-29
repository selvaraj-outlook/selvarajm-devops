data "aws_caller_identity" "current" {}
data "aws_partition" "current" {}

locals {
  account     = data.aws_caller_identity.current.account_id
  partition   = data.aws_partition.current.partition
  oidc_issuer = replace(data.aws_eks_cluster.this.identity[0].oidc[0].issuer, "https://", "")
  queue_name  = "karpenter-${var.cluster_name}"
}

################################################################################
# Node role: what Karpenter-launched nodes run as
################################################################################

data "aws_iam_policy_document" "node_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "node" {
  name               = "KarpenterNode-${var.cluster_name}"
  assume_role_policy = data.aws_iam_policy_document.node_assume.json
}

resource "aws_iam_role_policy_attachment" "node" {
  for_each = toset([
    "AmazonEKSWorkerNodePolicy",
    "AmazonEKS_CNI_Policy",
    "AmazonEC2ContainerRegistryReadOnly",
    "AmazonSSMManagedInstanceCore",
  ])
  role       = aws_iam_role.node.name
  policy_arn = "arn:${local.partition}:iam::aws:policy/${each.value}"
}

# Lets nodes join the cluster without editing aws-auth.
resource "aws_eks_access_entry" "node" {
  cluster_name  = var.cluster_name
  principal_arn = aws_iam_role.node.arn
  type          = "EC2_LINUX"
}

################################################################################
# Interruption handling: Spot interruptions, rebalance and health events -> SQS
################################################################################

resource "aws_sqs_queue" "interruption" {
  name                      = local.queue_name
  message_retention_seconds = 300
  sqs_managed_sse_enabled   = true
}

data "aws_iam_policy_document" "queue" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.interruption.arn]
    principals {
      type        = "Service"
      identifiers = ["events.amazonaws.com", "sqs.amazonaws.com"]
    }
  }
}

resource "aws_sqs_queue_policy" "interruption" {
  queue_url = aws_sqs_queue.interruption.url
  policy    = data.aws_iam_policy_document.queue.json
}

locals {
  interruption_events = {
    spot_interruption = { source = ["aws.ec2"], detail-type = ["EC2 Spot Instance Interruption Warning"] }
    rebalance         = { source = ["aws.ec2"], detail-type = ["EC2 Instance Rebalance Recommendation"] }
    state_change      = { source = ["aws.ec2"], detail-type = ["EC2 Instance State-change Notification"] }
    health            = { source = ["aws.health"], detail-type = ["AWS Health Event"] }
  }
}

resource "aws_cloudwatch_event_rule" "interruption" {
  for_each      = local.interruption_events
  name          = "karpenter-${var.cluster_name}-${each.key}"
  event_pattern = jsonencode(each.value)
}

resource "aws_cloudwatch_event_target" "interruption" {
  for_each = local.interruption_events
  rule     = aws_cloudwatch_event_rule.interruption[each.key].name
  arn      = aws_sqs_queue.interruption.arn
}

################################################################################
# Controller role (IRSA), scoped to this cluster's tagged resources
################################################################################

data "aws_iam_policy_document" "controller_assume" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = ["arn:${local.partition}:iam::${local.account}:oidc-provider/${local.oidc_issuer}"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:sub"
      values   = ["system:serviceaccount:${var.karpenter_namespace}:karpenter"]
    }
    condition {
      test     = "StringEquals"
      variable = "${local.oidc_issuer}:aud"
      values   = ["sts.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "controller" {
  name               = "KarpenterController-${var.cluster_name}"
  assume_role_policy = data.aws_iam_policy_document.controller_assume.json
}

data "aws_iam_policy_document" "controller" {
  statement {
    sid = "ReadOnly"
    actions = [
      "ec2:DescribeAvailabilityZones", "ec2:DescribeImages", "ec2:DescribeInstances",
      "ec2:DescribeInstanceTypeOfferings", "ec2:DescribeInstanceTypes", "ec2:DescribeLaunchTemplates",
      "ec2:DescribeSecurityGroups", "ec2:DescribeSpotPriceHistory", "ec2:DescribeSubnets",
      "pricing:GetProducts", "ssm:GetParameter",
    ]
    resources = ["*"]
  }
  statement {
    sid       = "LaunchUsingSharedResources"
    actions   = ["ec2:RunInstances", "ec2:CreateFleet"]
    resources = [for r in ["image", "snapshot", "security-group", "subnet"] : "arn:${local.partition}:ec2:${var.region}:*:${r}/*"]
  }
  statement {
    sid       = "LaunchWithOwnedLaunchTemplates"
    actions   = ["ec2:RunInstances", "ec2:CreateFleet"]
    resources = ["arn:${local.partition}:ec2:${var.region}:*:launch-template/*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/kubernetes.io/cluster/${var.cluster_name}"
      values   = ["owned"]
    }
  }
  statement {
    sid     = "CreateOnlyTaggedForCluster"
    actions = ["ec2:RunInstances", "ec2:CreateFleet", "ec2:CreateLaunchTemplate"]
    resources = [
      for r in ["fleet", "instance", "volume", "network-interface", "launch-template", "spot-instances-request"] :
      "arn:${local.partition}:ec2:${var.region}:*:${r}/*"
    ]
    condition {
      test     = "StringEquals"
      variable = "aws:RequestTag/kubernetes.io/cluster/${var.cluster_name}"
      values   = ["owned"]
    }
  }
  statement {
    sid       = "TagOnCreate"
    actions   = ["ec2:CreateTags"]
    resources = [for r in ["fleet", "instance", "volume", "network-interface", "launch-template", "spot-instances-request"] : "arn:${local.partition}:ec2:${var.region}:*:${r}/*"]
    condition {
      test     = "StringEquals"
      variable = "ec2:CreateAction"
      values   = ["RunInstances", "CreateFleet", "CreateLaunchTemplate"]
    }
  }
  statement {
    sid       = "ManageOwnedOnly"
    actions   = ["ec2:TerminateInstances", "ec2:DeleteLaunchTemplate", "ec2:CreateTags"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "aws:ResourceTag/kubernetes.io/cluster/${var.cluster_name}"
      values   = ["owned"]
    }
  }
  statement {
    sid       = "PassNodeRole"
    actions   = ["iam:PassRole"]
    resources = [aws_iam_role.node.arn]
  }
  statement {
    sid = "InstanceProfiles"
    actions = [
      "iam:CreateInstanceProfile", "iam:TagInstanceProfile", "iam:AddRoleToInstanceProfile",
      "iam:RemoveRoleFromInstanceProfile", "iam:DeleteInstanceProfile", "iam:GetInstanceProfile",
    ]
    resources = ["*"]
  }
  statement {
    sid       = "Interruption"
    actions   = ["sqs:DeleteMessage", "sqs:GetQueueUrl", "sqs:ReceiveMessage"]
    resources = [aws_sqs_queue.interruption.arn]
  }
  statement {
    sid       = "Cluster"
    actions   = ["eks:DescribeCluster"]
    resources = [data.aws_eks_cluster.this.arn]
  }
}

resource "aws_iam_role_policy" "controller" {
  name   = "karpenter-controller"
  role   = aws_iam_role.controller.id
  policy = data.aws_iam_policy_document.controller.json
}

################################################################################
# Helm: Karpenter and KEDA
################################################################################

resource "helm_release" "karpenter" {
  name       = "karpenter"
  repository = "oci://public.ecr.aws/karpenter"
  chart      = "karpenter"
  version    = var.karpenter_version
  namespace  = var.karpenter_namespace
  wait       = true

  values = [yamlencode({
    settings = {
      clusterName       = var.cluster_name
      clusterEndpoint   = data.aws_eks_cluster.this.endpoint
      interruptionQueue = aws_sqs_queue.interruption.name
    }
    serviceAccount = {
      annotations = { "eks.amazonaws.com/role-arn" = aws_iam_role.controller.arn }
    }
    controller = {
      resources = {
        requests = { cpu = "500m", memory = "512Mi" }
        limits   = { memory = "1Gi" }
      }
    }
  })]
}

resource "helm_release" "keda" {
  name             = "keda"
  repository       = "https://kedacore.github.io/charts"
  chart            = "keda"
  version          = var.keda_version
  namespace        = "keda"
  create_namespace = true
}
