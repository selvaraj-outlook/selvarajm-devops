# Hi, I'm Selvaraj M 👋

**Senior Cloud Engineer at Presidio** · Chennai, India<br>
AWS · Azure · Kubernetes · Terraform · CI/CD · Cloud Governance

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Selvaraj%20M-0A66C2?logo=linkedin&logoColor=white)](https://www.linkedin.com/in/selvarajm-50939520a)
![AWS SAA](https://img.shields.io/badge/AWS-Solutions%20Architect%20Associate-FF9900?logo=amazonwebservices&logoColor=white)
![Terraform Associate](https://img.shields.io/badge/HashiCorp-Terraform%20Associate-7B42BC?logo=terraform&logoColor=white)

5+ years in IT and cloud infrastructure. I build AWS and Azure platforms, CI/CD pipelines and automation, and I like turning manual, ticket-driven work into code.

- 🏗️ Governance for a 60+ account AWS Control Tower estate, managed entirely as Terraform
- ⚙️ CI/CD on Azure DevOps, GitLab CI and GitHub Actions, authenticated with OIDC (no static cloud keys)
- ☸️ Production Kubernetes on Amazon EKS and Azure AKS
- 💰 Cost controls and observability: AWS Budgets, CloudWatch, Grafana

## 📂 Projects

Each project lives on its own branch of this repo.

### ☁️ Platform & Kubernetes

| Project | What it shows | Branch |
|---|---|---|
| **GPU LLM inference on EKS** | vLLM on Amazon EKS with GPU node groups, Terraform (VPC, EKS, ECR, IRSA), Kustomize overlays for dev/staging/prod, and a GitHub Actions pipeline using OIDC | [`k8s-vllm`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/k8s-vllm) |
| **AWS Service Catalog platform** | Self-service provisioning across an AWS Organization: 32 secure-by-default products, launch constraints, org-wide sharing, StackSets, cross-account DNS Lambda, OIDC plan/apply pipelines | [`aws-service-catalog`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/aws-service-catalog) |

### 🤖 MLOps

| Project | What it shows | Branch |
|---|---|---|
| **MLflow on EKS** | Tracking server and model registry: RDS PostgreSQL (Secrets Manager password), S3 artifacts, IRSA, internal ALB | [`mlflow-on-eks`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/mlflow-on-eks) |
| **KServe model serving** | Serverless inference with Knative and Kourier, immutable S3 model versions, canary rollout with promote/rollback, gated release pipeline | [`kserve-model-serving`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/kserve-model-serving) |
| **SageMaker Pipelines** | Preprocess → train → evaluate → accuracy gate → Model Registry; EventBridge + Lambda deploy on approval (blue/green) | [`sagemaker-pipelines`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/sagemaker-pipelines) |
| **Kubeflow training pipeline** | KFP v2 components with typed artifacts, accuracy gate, publish to S3 via IRSA; KFP 2.3 standalone install | [`kubeflow-training-pipeline`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/kubeflow-training-pipeline) |
| **Feast feature store** | S3 offline store and registry, DynamoDB online store, point-in-time training data, hourly materialization CronJob | [`feast-feature-store`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/feast-feature-store) |
| **Model drift monitoring** | PSI, KS and chi-square drift job → Pushgateway → Prometheus alerts and Grafana dashboard as code | [`model-drift-monitoring`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/model-drift-monitoring) |
| **Bedrock RAG platform** | Knowledge Bases + OpenSearch Serverless, guardrails (prompt attack, PII), IAM-auth API, auto re-ingestion, evaluation gate | [`bedrock-rag-platform`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/bedrock-rag-platform) |
| **Karpenter GPU autoscaling** | Spot-first GPU NodePools on Bottlerocket, interruption handling, vLLM with KEDA scale-to-zero, cost report | [`karpenter-gpu-autoscaling`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/karpenter-gpu-autoscaling) |
| **ML CI/CD with GitHub Actions** | Data validation, champion/challenger gate, model card, App Runner staging → approval → production, OIDC per environment | [`ml-cicd-github-actions`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/ml-cicd-github-actions) |
| **Azure ML MLOps** | Terraform workspace and scale-to-zero cluster, AML pipeline with gate, blue/green managed endpoint, Azure DevOps with OIDC | [`azureml-mlops`](https://github.com/selvaraj-outlook/selvarajm-devops/tree/azureml-mlops) |

Every project has Terraform, CI (validation and tests on each push), a README with an architecture diagram, and deploy and clean-up steps.

## 🛠️ Tech stack

- **Cloud:** AWS · Azure
- **IaC:** Terraform · CloudFormation · Bicep
- **Containers:** Kubernetes (EKS, AKS) · Docker · Kustomize · ArgoCD · Karpenter · KEDA
- **CI/CD:** Azure DevOps · GitLab CI · GitHub Actions · AWS CodePipeline
- **Governance:** Control Tower · Organizations · SCPs · IAM Identity Center · Service Catalog
- **MLOps:** MLflow · SageMaker · Kubeflow · KServe · Feast · Bedrock · Azure ML · vLLM
- **Observability:** CloudWatch · Grafana · Prometheus · Datadog
- **Scripting:** Python · Bash

## 🎓 Certifications
- AWS Certified Solutions Architect – Associate
- HashiCorp Certified: Terraform Associate

## 📫 Contact
[LinkedIn](https://www.linkedin.com/in/selvarajm-50939520a)
