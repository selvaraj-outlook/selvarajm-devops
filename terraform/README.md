# AWS infrastructure

Terraform for the AWS resources the deployment pipeline assumes but that were never codified: the VPC, the EKS cluster, the GPU nodes, ECR, and the IAM role GitHub Actions federates into.

This is a separate layer from `base/` and `overlays/`. Those are Kubernetes objects applied *into* a cluster; this creates the cluster. Terraform runs first, always.

## What it creates

| Area | Resources |
|---|---|
| Network | VPC, public/private subnets across `az_count` AZs, IGW, NAT, S3 gateway endpoint and interface endpoints for ECR/STS/logs/EC2 |
| Cluster | EKS control plane, KMS-encrypted secrets, control plane logs to CloudWatch, IRSA OIDC provider |
| Nodes | `system` node group (CPU, for CoreDNS and the EBS CSI controller) and `gpu` node group (NVIDIA AMI, labelled and tainted for the workload) |
| Add-ons | vpc-cni, kube-proxy, coredns, aws-ebs-csi-driver, eks-pod-identity-agent |
| Registry | ECR repository with scan-on-push and a lifecycle policy |
| CI identity | GitHub OIDC provider, deploy role, and the EKS access entry that lets it run `kubectl` |

## Prerequisites

**G-instance vCPU quota.** New accounts have 0, which means the GPU node group cannot launch anything. Check it:

```sh
aws service-quotas get-service-quota --service-code ec2 --quota-code L-DB2E81BA --region us-east-1
```

A `g5.2xlarge` is 8 vCPU, and each environment namespace runs one replica holding one whole GPU, so three concurrent environments need 24 vCPU. Request an increase in the console, or set `request_gpu_quota_increase = true` (asynchronous; Terraform will wait on AWS).

Until it's approved, apply with the pool empty and scale up later:

```hcl
gpu_min_size     = 0
gpu_desired_size = 0
```

A `check` block warns at plan time if the quota can't support the configured pool, so you find out in seconds rather than fifteen minutes into an apply.

## First apply (from a workstation)

The pipeline runs Terraform, but it can't run the *first* one: the role CI assumes is created by this configuration. So the first apply is local, then CI takes over.

```sh
cd terraform

# 1. State bucket. Cannot be managed by the Terraform that stores state in it.
./scripts/bootstrap-state.sh k8s-vllm-tfstate-123456789012 us-east-1

# 2. Point Terraform at it. backend.hcl already names the bucket above.
cp terraform.tfvars.example terraform.tfvars

terraform init -backend-config=backend.hcl
terraform plan
terraform apply
```

Then wire GitHub up from the outputs:

```sh
gh secret   set AWS_ROLE_ARN           --body "$(terraform output -raw github_actions_role_arn)"
gh secret   set AWS_TERRAFORM_ROLE_ARN --body "$(terraform output -raw terraform_ci_role_arn)"
gh secret   set EKS_CLUSTER_NAME       --body "$(terraform output -raw cluster_name)"
gh variable set TF_STATE_BUCKET        --body k8s-vllm-tfstate-123456789012
```

## Terraform in the pipeline

`terraform-plan` and `terraform-apply` run ahead of everything else, because `build-and-push` needs the ECR repository and the deploy jobs need the cluster.

```
terraform-plan -> terraform-apply -> build-and-push -> bootstrap-cluster -> deploy-dev -> ...
```

`terraform-plan` runs on every push and on pull requests that touch `terraform/**`. It uses `-detailed-exitcode`, so it reports whether anything actually changed and only uploads a plan artifact when it did.

`terraform-apply` applies that saved plan rather than re-planning, so what ran is exactly what was reviewed. It is skipped unless all of these hold:

- the trigger is not a pull request
- the plan found changes
- the `TERRAFORM_AUTO_APPLY` repository variable is `true`

When it skips, the application jobs still run. `skipped` is the normal outcome when infrastructure is already current.

### GitHub configuration

| Kind | Name | Purpose |
|---|---|---|
| Secret | `AWS_ROLE_ARN` | deploy role, used by build and the deploy jobs |
| Secret | `AWS_TERRAFORM_ROLE_ARN` | infra role. Falls back to `AWS_ROLE_ARN` if unset |
| Secret | `EKS_CLUSTER_NAME` | must equal the `cluster_name` output |
| Variable | `TF_STATE_BUCKET` | required; the plan job fails fast without it |
| Variable | `TERRAFORM_AUTO_APPLY` | `true` to let CI apply |
| Variable | `DEPLOY_STAGING`, `DEPLOY_PROD` | `true` to enable those environments |

Environments: `infra-plan` unprotected, `infra` with required reviewers, plus `dev`, `staging`, `prod`.

The two infra environments exist because the OIDC `sub` claim is derived from the job's environment. Plan needs to authenticate without waiting for approval, apply needs the approval gate, and they cannot share one environment and do both. The Terraform CI role trusts only these two, so nothing in a deploy job can reach infrastructure permissions.

### Why apply is gated rather than automatic

An unreviewed `terraform apply` on every push to `main` can delete a cluster because someone renamed a variable. The plan output is the review artifact; `TERRAFORM_AUTO_APPLY` plus reviewers on the `infra` environment is the seatbelt. Turn it on once you trust the plan diffs you're seeing.

## If the OIDC provider already exists

Everything here is created from scratch, with one account-wide exception. IAM permits at most one OIDC provider per URL per account, so if `123456789012` already has one for `token.actions.githubusercontent.com` — another repository may have created it — the apply fails with `EntityAlreadyExists`. Point the configuration at the existing one instead:

```hcl
# ci.auto.tfvars
create_github_oidc_provider = false
```

The trust policy is unaffected either way; it is scoped by the `sub` claim, not by who owns the provider.

## Things worth changing before this is production

The deploy role in the existing account carries `AdministratorAccess` and its trust policy includes `repo:core-projects-factory/*:environment:*`, meaning any repository in that org can assume an admin role. Both are preserved as-is so the import causes no change. A least-privilege inline policy is attached alongside; once you've confirmed it's sufficient:

```sh
aws iam detach-role-policy --role-name GitHubActions-DeploymentRole \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

and drop the wildcard subject from `github_allowed_subjects`.

The API server endpoint is public and open to `0.0.0.0/0`, because GitHub-hosted runners egress from ranges that change. Narrowing `cluster_endpoint_public_access_cidrs` means moving to self-hosted runners or a VPN.

The deploy role gets `AmazonEKSClusterAdminPolicy` because the pipeline's `kubectl apply -k` creates Namespaces. Move namespace creation into Terraform and you can downgrade it to `AmazonEKSAdminPolicy` scoped to `workload_namespaces`.

## Cost

The idle baseline is roughly $0.40/hour: control plane, two `m6i.large`, one NAT gateway, and 15 interface-endpoint ENIs across 3 AZs. A `g5.2xlarge` adds about $1.20/hour on demand. Approximate, so confirm against the pricing calculator.

For a throwaway account, `az_count = 2` and trimming `aws_vpc_endpoint.interface` cuts the idle burn most.

## Coupling to the Kubernetes layer

Three things must agree across the two layers, and breakage is silent:

- The GPU node group's `nvidia.com/gpu.present=true` label and `nvidia.com/gpu` taint are what `base/deployment.yaml` selects and tolerates.
- The `aws-ebs-csi-driver` add-on is what lets the `model-cache` PVC bind. The gp3 StorageClass itself lives in `cluster-bootstrap/`.
- The GPU node group is pinned to a single AZ, because the model-cache EBS volume is zonal and a pod rescheduled into another AZ can't attach it.
