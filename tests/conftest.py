import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for sub in ("src/prep", "src/train", "src/register", "scripts"):
    sys.path.insert(0, str(ROOT / sub))
