#!/usr/bin/env python3
"""Structural checks without PyYAML; semantic behavior requires forward testing."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
errors, names = [], []
for file in sorted((ROOT / ".agents/skills").glob("*/SKILL.md")):
    text = file.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3:
        errors.append(f"{file.parent.name}: missing frontmatter")
        continue
    match = re.search(r"^name: ([-a-z0-9]+)$", parts[1], re.M)
    if not match or match.group(1) != file.parent.name:
        errors.append(f"{file.parent.name}: invalid name")
    if not re.search(r"^description: .+", parts[1], re.M):
        errors.append(f"{file.parent.name}: missing description")
    for link in re.findall(r"\]\(([^)]+)\)", text):
        if not link.startswith(("http:", "https:")) and not (file.parent / link).resolve().is_file():
            errors.append(f"{file.parent.name}: missing reference {link}")
    metadata = (file.parent / "agents/openai.yaml").read_text(encoding="utf-8")
    if "$"+file.parent.name not in metadata:
        errors.append(f"{file.parent.name}: prompt does not mention skill")
    names.append(file.parent.name)
if len(names) != 8:
    errors.append(f"Expected 8 skills, found {len(names)}")
print(json.dumps({"skills": names, "passed": not errors, "errors": errors, "scope": "structure and reference links; not semantic routing accuracy"}, ensure_ascii=False, indent=2))
raise SystemExit(1 if errors else 0)
