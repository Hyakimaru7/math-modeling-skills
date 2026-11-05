#!/usr/bin/env python3
"""Build a complete portable source-and-skills archive, with optional executed cases."""
import argparse
import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output", type=Path, default=ROOT.parent / "math-modeling-skills.zip")
args = parser.parse_args()
excluded = {".git", ".venv", "__pycache__", ".cache", "build", "dist", "runs"}
args.output.parent.mkdir(parents=True, exist_ok=True)
count = 0
with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT)
        if not path.is_file() or path.resolve() == args.output.resolve():
            continue
        if path.name == ".DS_Store":
            continue
        if any(part in excluded or part.endswith(".egg-info") for part in relative.parts):
            continue
        if path.suffix in {".pyc", ".aux", ".out", ".log"}:
            continue
        archive.write(path, "math-modeling-skills/"+relative.as_posix())
        count += 1
checksum = hashlib.sha256(args.output.read_bytes()).hexdigest()
args.output.with_suffix(".zip.sha256").write_text(f"{checksum}  {args.output.name}\n", encoding="utf-8")
print(f"{args.output}: {count} files; sha256={checksum}")
