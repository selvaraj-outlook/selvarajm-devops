.PHONY: validate test compile install-kfp ui
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
test:
	ruff check .
	pytest -q
compile:
	python -m pipelines.training_pipeline
install-kfp:
	kubectl apply -k k8s/kfp/cluster-scoped
	kubectl wait --for condition=established --timeout=60s crd/applications.app.k8s.io
	kubectl apply -k k8s/kfp/platform
	kubectl -n kubeflow wait --for=condition=Available deployment --all --timeout=10m
ui:
	kubectl -n kubeflow port-forward svc/ml-pipeline-ui 8080:80
