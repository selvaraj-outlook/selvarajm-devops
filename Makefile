.PHONY: validate test bootstrap
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
	for d in k8s/platform k8s/models/overlays/stable k8s/models/overlays/canary; do \
	  kustomize build $$d | kubeconform -strict -summary -ignore-missing-schemas -; done
test:
	ruff check .
	pytest -q
bootstrap:
	kubectl apply -k k8s/platform
	kubectl -n knative-serving wait --for=condition=Ready knativeserving/knative-serving --timeout=10m
