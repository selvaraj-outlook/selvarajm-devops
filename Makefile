.PHONY: test validate data train deploy
test:
	ruff check .
	pytest -q
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
data:
	python scripts/make_data.py
train: data
	az ml environment create --file aml/environment/environment.yaml
	az ml job create --file aml/pipeline.yaml --stream
deploy:
	scripts/blue_green.sh $(RG) $(WS) breast-cancer-ep
