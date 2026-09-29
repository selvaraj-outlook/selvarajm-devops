.PHONY: validate test phase1 index phase2 docs ask
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
test:
	ruff check .
	pytest -q
phase1:
	terraform -chdir=terraform apply
index:
	python scripts/create_index.py --endpoint "$$(terraform -chdir=terraform output -raw collection_endpoint)"
phase2:
	terraform -chdir=terraform apply -var create_knowledge_base=true
docs:
	aws s3 sync docs/sample "s3://$$(terraform -chdir=terraform output -raw docs_bucket)/"
ask:
	@python scripts/ask.py --url "$$(terraform -chdir=terraform output -raw rag_api_url)" "$(Q)"
