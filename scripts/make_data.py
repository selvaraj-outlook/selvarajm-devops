"""Write the scikit-learn breast-cancer dataset as CSV (the pipeline's raw input)."""

from pathlib import Path

from sklearn.datasets import load_breast_cancer

FEATURES = ["mean radius", "mean texture", "mean perimeter", "mean area", "mean smoothness"]


def build():
    X, y = load_breast_cancer(return_X_y=True, as_frame=True)
    return X[FEATURES].assign(target=y)


if __name__ == "__main__":
    out = Path("data/breast_cancer.csv")
    out.parent.mkdir(exist_ok=True)
    build().to_csv(out, index=False)
    print(f"wrote {out}")
