.PHONY: validate test build
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
	kustomize build k8s/overlays/dev | kubeconform -strict -summary -ignore-missing-schemas -
test:
	ruff check .
	pytest -q
build:
	docker build -f docker/Dockerfile -t model-drift-job:local .
