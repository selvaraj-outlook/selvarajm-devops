.PHONY: test train serve validate
test:
	ruff check .
	pytest -q
train:
	PYTHONPATH=src python -m mlpipe.train --out artifacts
serve: train
	PYTHONPATH=src MODEL_DIR=artifacts uvicorn mlpipe.serve:app --port 8080
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
