# AWS Service Catalog — self-service provisioning with Terraform

A reusable Terraform module that stands up an **AWS Service Catalog portfolio** in a shared-services account and shares it across an AWS Organization, so teams can launch pre-approved, secure-by-default infrastructure without tickets.

> All account IDs, domains and names in this branch are placeholders (`111111111111`, `app.example.com`, `acme`). Replace them with your own values before applying.

## What it does
- **32 curated products** as CloudFormation templates — S3, DynamoDB, RDS, SQS/SNS, KMS, Secrets Manager, ACM, Route 53, VPC, ECS, ECR, Lambda, API Gateway, CloudFront, WAF, Step Functions, CodePipeline and more — each encrypted and locked down by default.
- **Launch constraints** so end users provision through a scoped launch role, never with their own admin rights.
- **Org-wide sharing** of the portfolio, plus an optional service-managed StackSet that deploys the end-user role into every member account.
- **Cross-account DNS** via a Python Lambda so a spoke account can create records in a central hosted zone, limited to an allowlist of domains.
- **GitHub Actions with OIDC** — `terraform plan` on pull requests and a manual, confirmation-gated `apply`. No static AWS keys in CI.

## Layout
| Path | Purpose |
|---|---|
| `service-catalog.tf` | Root config: which products to register and who can launch them |
| `modules/service-catalog/` | The module: portfolio, products, constraints, sharing, StackSets |
| `modules/service-catalog/cloudformation/products/` | The product templates |
| `modules/service-catalog/lambda/` | Cross-account Route 53 handler |
| `.github/workflows/` | Plan and apply pipelines |
| `.github/oidc-role.yaml`, `.github/docs/oidc-setup.md` | IAM role and setup guide for GitHub OIDC |

See [`modules/service-catalog/README.md`](modules/service-catalog/README.md) for the full module reference.

## Tech
Terraform · AWS Service Catalog · AWS Organizations · CloudFormation StackSets · IAM · Lambda (Python) · Route 53 · GitHub Actions · OIDC
