.PHONY: validate test pools workload cost
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
	for d in k8s/karpenter k8s/workload; do kustomize build $$d | kubeconform -strict -summary -ignore-missing-schemas -; done
test:
	ruff check .
	pytest -q
pools:
	kubectl apply -k k8s/karpenter
workload:
	kubectl apply -k k8s/workload
cost:
	kubectl get nodes -o json | python scripts/gpu_cost_report.py
