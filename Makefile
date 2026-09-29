.PHONY: validate test sample-data
validate:
	terraform -chdir=terraform fmt -check -recursive
	terraform -chdir=terraform init -backend=false -input=false >/dev/null
	terraform -chdir=terraform validate
test:
	ruff check .
	pytest -q
# Upload a sample dataset (scikit-learn breast cancer) to s3://$(BUCKET)/data/raw/
sample-data:
	python -c "from sklearn.datasets import load_breast_cancer as l; X,y=l(return_X_y=True,as_frame=True); X.assign(target=y).to_csv('/tmp/data.csv',index=False)"
	aws s3 cp /tmp/data.csv s3://$(BUCKET)/data/raw/data.csv
