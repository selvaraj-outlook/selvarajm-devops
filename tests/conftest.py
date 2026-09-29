import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline" / "code"))
sys.path.insert(0, str(ROOT / "lambda" / "deployer"))
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
