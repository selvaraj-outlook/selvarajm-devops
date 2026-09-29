.PHONY: validate test data apply
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
	kustomize build k8s/overlays/dev | kubeconform -strict -summary -
test:
	ruff check .
	pytest -q
# Generate sample data and upload it: make data BUCKET=<bucket>
data:
	python scripts/generate_data.py --out data/driver_hourly_stats.parquet
	aws s3 cp data/driver_hourly_stats.parquet s3://$(BUCKET)/data/
apply:
	cd feature_repo && FEAST_BUCKET=$(BUCKET) FEAST_DATA_ROOT=s3://$(BUCKET)/data feast apply
