.PHONY: validate test fmt build

validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
	kustomize build k8s/overlays/dev | kubeconform -strict -summary -

test:
	ruff check .
	pytest -q

fmt:
	terraform -chdir=terraform fmt -recursive
	ruff format .

build:
	docker build -t mlflow-server:local docker/
