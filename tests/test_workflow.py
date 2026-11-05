from __future__ import annotations

import copy
import json
import math
import shutil
from pathlib import Path
import tempfile
import unittest

from math_modeling import models
from math_modeling.core import ModelingError, load_problem, read_json, write_json
from math_modeling.paper import render_content
from math_modeling.pipeline import audit, init_workspace, log_ai, run, status


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="mm-eval-")
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def case(self, kind="allocation"):
        return init_workspace(self.root / kind, kind)

    def config(self, path, update):
        p = read_json(path / "problem.json")
        update(p)
        write_json(path / "problem.json", p)

    def execute(self, path, until="validate", force=False, messages=None):
        return run(path, until=until, force=force, engine="reportlab", emit=messages.append if messages is not None else lambda x: None)

    def test_known_integer_optimum_and_independent_checks(self):
        root = self.case()
        self.execute(root)
        result = read_json(root / "solution.json")
        self.assertAlmostEqual(result["metrics"]["objective"], 605)
        self.assertEqual(result["solver"]["x"], [9, 7, 0])
        self.assertTrue(read_json(root / "validation.json")["passed"])
        self.assertLessEqual(result["metrics"]["objective"], result["metrics"]["relaxation_upper_bound"]+1e-8)

    def test_profit_scaling_preserves_solution(self):
        root = self.case()
        p = load_problem(root)
        d = models.prepare(p, root)
        doubled = copy.deepcopy(d)
        doubled["profits"] = [2*x for x in d["profits"]]
        first = models.solve(p, d, root, root / "figures")
        second = models.solve(p, doubled, root, root / "figures")
        self.assertEqual(first["solver"]["x"], second["solver"]["x"])
        self.assertAlmostEqual(second["metrics"]["objective"], first["metrics"]["objective"]*2)

    def test_resource_expansion_does_not_reduce_optimum(self):
        root = self.case()
        p = load_problem(root)
        r = models.solve(p, models.prepare(p, root), root, root / "figures")
        values = [x["objective"] for x in r["tables"]["sensitivity"]]
        self.assertEqual(sorted(values), values)

    def test_infeasible_problem_retains_status_and_blocks_paper(self):
        root = self.case()
        (root / "raw/products.csv").write_text("product,profit,min_units,max_units,labor,material\nA,10,9,10,100,100\n", encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root, "review")
        self.assertEqual(read_json(root / "solution.json")["status"], "infeasible")
        self.assertFalse((root / "paper/paper.pdf").exists())
        self.assertEqual(read_json(root / "state.json")["stages"]["validate"]["status"], "failed")

    def test_duplicate_product_rejected(self):
        root = self.case()
        file = root / "raw/products.csv"
        file.write_text(file.read_text().replace("产品乙", "产品甲"), encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root, "data")

    def test_nonfinite_data_rejected(self):
        root = self.case()
        file = root / "raw/products.csv"
        file.write_text(file.read_text().replace(",40,", ",nan,"), encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root, "data")

    def test_missing_unit_rejected(self):
        root = self.case()
        self.config(root, lambda p: p["units"].pop("labor"))
        with self.assertRaises(ModelingError):
            self.execute(root, "data")

    def test_duplicate_date_rejected(self):
        root = self.case("forecast")
        file = root / "raw/demand.csv"
        file.write_text(file.read_text().replace("2026-01-02", "2026-01-01"), encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root, "data")

    def test_date_gap_rejected(self):
        root = self.case("forecast")
        file = root / "raw/demand.csv"
        lines = file.read_text().splitlines()
        file.write_text("\n".join(lines[:5]+lines[6:])+"\n", encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root, "data")

    def test_forecast_test_values_cannot_change_training_selection(self):
        root = self.case("forecast")
        p = load_problem(root)
        data = models.prepare(p, root)
        changed = copy.deepcopy(data)
        changed["y"][-data["holdout"]:] = [x+10000 for x in changed["y"][-data["holdout"]:]]
        a = models.solve(p, data, root, root / "figures")
        b = models.solve(p, changed, root, root / "figures")
        self.assertEqual(a["selected_model"], b["selected_model"])
        self.assertEqual(a["cv_scores"], b["cv_scores"])
        self.assertGreater(b["metrics"]["holdout_rmse"], a["metrics"]["holdout_rmse"]+9000)

    def test_exact_linear_series_forecast(self):
        root = self.case("forecast")
        p = load_problem(root)
        d = models.prepare(p, root)
        d["y"] = [10+2*t for t in range(len(d["y"]))]
        r = models.solve(p, d, root, root / "figures")
        self.assertLess(r["metrics"]["holdout_rmse"], 1e-8)
        self.assertAlmostEqual(r["tables"]["forecast"][0]["predicted"], 10+2*len(d["y"]), places=7)
        self.assertTrue(models.validate(p, d, r, root)["passed"])

    def test_forged_forecast_actuals_fail_validation(self):
        root = self.case("forecast")
        p = load_problem(root)
        d = models.prepare(p, root)
        r = models.solve(p, d, root, root / "figures")
        r["tables"]["holdout"][0]["actual"] += 100
        self.assertFalse(models.validate(p, d, r, root)["passed"])

    def test_forecast_complete_pdf_and_audit(self):
        root = self.case("forecast")
        self.execute(root, "review")
        self.assertTrue(audit(root)["passed"])
        self.assertTrue(status(root)["current"])
        from pypdf import PdfReader
        self.assertGreater(len(PdfReader(root / "paper/paper.pdf").pages), 0)

    def test_custom_adapter_complete_pdf_and_audit(self):
        root = self.case("custom")
        self.execute(root, "review")
        self.assertAlmostEqual(read_json(root / "solution.json")["metrics"]["center"], 5)
        self.assertAlmostEqual(read_json(root / "solution.json")["metrics"]["loss"], 20)
        self.assertTrue(audit(root)["passed"])

    def test_stop_and_resume_preserves_finished_calculation(self):
        root = self.case()
        self.execute(root, "solve")
        old = (root / "solution.json").read_bytes()
        messages = []
        self.execute(root, "review", messages=messages)
        self.assertEqual((root / "solution.json").read_bytes(), old)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 4)

    def test_unchanged_run_reuses_all_stages(self):
        root = self.case("custom")
        self.execute(root, "review")
        messages = []
        self.execute(root, "review", messages=messages)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 7)

    def test_input_change_marks_stale_and_updates_claims(self):
        root = self.case("custom")
        self.execute(root, "review")
        old = read_json(root / "solution.json")["result_id"]
        (root / "raw/observations.csv").write_text("value\n4\n6\n8\n10\n", encoding="utf-8")
        self.assertFalse(status(root)["current"])
        self.execute(root, "review")
        self.assertNotEqual(old, read_json(root / "solution.json")["result_id"])
        self.assertEqual(read_json(root / "paper/claims.json")[0]["value"], 7)

    def test_added_attachment_invalidates_inputs(self):
        root = self.case("custom")
        self.execute(root, "review")
        (root / "raw/notes.txt").write_text("new source", encoding="utf-8")
        self.assertFalse(status(root)["current"])

    def test_only_prose_change_preserves_solve(self):
        root = self.case("custom")
        self.execute(root, "review")
        c = read_json(root / "paper/content.json")
        c["sections"][0]["text"] += "该结果适用于等权平方损失。"
        write_json(root / "paper/content.json", c)
        messages = []
        self.execute(root, "review", messages=messages)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 5)

    def test_ai_log_change_only_rebuilds_paper_and_review(self):
        root = self.case("custom")
        self.execute(root, "review")
        log_ai(root, "test-harness", "接口记录测试", "", "test")
        messages = []
        self.execute(root, "review", messages=messages)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 5)
        self.assertFalse(any("记录为空" in w for w in audit(root)["warnings"]))

    def test_tampered_result_detected_without_mutation(self):
        root = self.case("custom")
        self.execute(root, "review")
        r = read_json(root / "solution.json")
        r["metrics"]["center"] = 999
        write_json(root / "solution.json", r)
        self.assertFalse(audit(root)["passed"])
        self.assertEqual(read_json(root / "solution.json")["metrics"]["center"], 999)

    def test_deleted_pdf_rebuilds_paper(self):
        root = self.case("custom")
        self.execute(root, "review")
        (root / "paper/paper.pdf").unlink()
        messages = []
        self.execute(root, "review", messages=messages)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 5)
        self.assertTrue((root / "paper/paper.pdf").is_file())

    def test_missing_figure_recomputes_calculation(self):
        root = self.case()
        self.execute(root)
        (root / "figures/allocation.png").unlink()
        messages = []
        self.execute(root, messages=messages)
        self.assertEqual(sum(x.startswith("[cached]") for x in messages), 3)
        self.assertTrue((root / "figures/allocation.png").is_file())

    def test_unbound_prose_number_is_rejected(self):
        p = {"sources": [], "questions": []}
        with self.assertRaises(ModelingError):
            render_content({"abstract": "改善了99%。", "sections": []}, p, {"metrics": {}, "result_id": "x"})

    def test_unknown_reference_is_rejected(self):
        with self.assertRaises(ModelingError):
            render_content({"abstract": "方法{{cite:invented}}。", "sections": []}, {"sources": [], "questions": []}, {"metrics": {}, "result_id": "x"})

    def test_unanswered_question_blocks_paper(self):
        with self.assertRaises(ModelingError):
            render_content({"abstract": "摘要", "sections": []}, {"sources": [], "questions": [{"id": "Q1"}]}, {"metrics": {}, "result_id": "x"})

    def test_cyclic_question_dependency_rejected(self):
        root = self.case()
        self.config(root, lambda p: p["questions"][0].update({"depends_on": ["Q2"]}))
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_data_path_escape_rejected(self):
        root = self.case()
        self.config(root, lambda p: p.update({"data_file": "../outside.csv"}))
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_unknown_builtin_task_cannot_claim_coverage(self):
        root = self.case()
        self.config(root, lambda p: p["questions"][0].update({"task": "vehicle_routing"}))
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_unresolved_assumptions_stop_before_compute(self):
        root = self.case()
        self.config(root, lambda p: p.update({"unresolved": ["容量单位未明确"]}))
        with self.assertRaises(ModelingError):
            self.execute(root)
        self.assertFalse((root / "solution.json").exists())

    def test_initialization_never_overwrites_nonempty_workspace(self):
        root = self.case()
        with self.assertRaises(ModelingError):
            init_workspace(root, "forecast")
        self.assertEqual(load_problem(root)["kind"], "allocation")

    def test_json_nan_cannot_enter_config(self):
        root = self.case()
        file = root / "problem.json"
        file.write_text(file.read_text().replace('"labor": 25', '"labor": NaN'), encoding="utf-8")
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_human_verification_requires_person_and_date(self):
        root = self.case()
        self.config(root, lambda p: p["sources"][0].update({"verification": "human_verified"}))
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_parameter_binding_reads_declared_input(self):
        content = {"abstract": "预测 {{param:horizon|.0f}} 日。", "sections": []}
        abstract, _, claims, _ = render_content(content, {"sources": [], "questions": [], "horizon": 7}, {"metrics": {}, "result_id": "x"})
        self.assertEqual(abstract, "预测 7 日。")
        self.assertEqual(claims[0]["kind"], "param")

    def test_self_reported_success_cannot_override_failed_checks(self):
        root = self.case("custom")
        adapter = root / "adapter.py"
        adapter.write_text(adapter.read_text().replace('"passed": abs(gradient)<1e-10', '"passed": False').replace('"passed": all(x["passed"] for x in checks)', '"passed": True'), encoding="utf-8")
        with self.assertRaises(ModelingError):
            self.execute(root)
        self.assertFalse(read_json(root / "validation.json")["passed"])

    def test_nondictionary_problem_rejected(self):
        root = self.case()
        write_json(root / "problem.json", [])
        with self.assertRaises(ModelingError):
            load_problem(root)

    def test_source_control_characters_rejected(self):
        root = self.case()
        self.config(root, lambda p: p["sources"][0].update({"url": "https://example.org/}unsafe"}))
        with self.assertRaises(ModelingError):
            load_problem(root)

    @unittest.skipUnless(shutil.which("xelatex"), "XeLaTeX is optional; portable preview is tested separately")
    def test_custom_xelatex_with_no_sources(self):
        root = self.case("custom")
        run(root, engine="xelatex", emit=lambda x: None)
        self.assertTrue(audit(root)["passed"])
        self.assertEqual(read_json(root / "paper/build.json")["engine"], "xelatex")


if __name__ == "__main__":
    unittest.main()
