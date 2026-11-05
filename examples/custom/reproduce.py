from pathlib import Path
from math_modeling.pipeline import run
run(Path(__file__).resolve().parent, force=True)
