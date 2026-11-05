#!/usr/bin/env python3
"""Run observable mathematical, reproduction and integrity evaluations."""
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from math_modeling.core import versions


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.records = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.records.append({"id": test.id(), "status": "passed"})

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.records.append({"id": test.id(), "status": "failed", "detail": self._exc_info_to_string(err, test)})

    def addError(self, test, err):
        super().addError(test, err)
        self.records.append({"id": test.id(), "status": "error", "detail": self._exc_info_to_string(err, test)})

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.records.append({"id": test.id(), "status": "skipped", "detail": reason})


suite = unittest.defaultTestLoader.discover(str(ROOT / "tests"))
result = unittest.TextTestRunner(verbosity=2, resultclass=RecordingResult).run(suite)
report = {"generated_at": datetime.now(timezone.utc).isoformat(), "tests": result.testsRun,
          "passed": sum(x["status"] == "passed" for x in result.records), "successful": result.wasSuccessful(),
          "skipped": len(result.skipped),
          "versions": versions(), "cases": result.records,
          "scope": "Deterministic execution and artifact contracts. Native LLM routing prompts are provided separately and are not claimed as evaluated."}
(ROOT / "evals/latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
raise SystemExit(0 if result.wasSuccessful() else 1)
