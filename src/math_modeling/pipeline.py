from __future__ import annotations

import json
import shutil
from pathlib import Path

from . import models
from .core import ModelingError, digest, load_problem, now, read_json, sha, versions, within, write_csv, write_json
from .figures import create_figures
from .paper import build, lookup

STAGES = ["analyze", "data", "model", "solve", "validate", "paper", "review"]
ASSETS = Path(__file__).parent / "assets"


def init_workspace(path, case="allocation"):
    target = Path(path).resolve()
    if target.exists() and any(target.iterdir()):
        raise ModelingError("目标目录非空；请选择空目录，已有项目使用 mm run")
    source = ASSETS / "cases" / case
    if not source.is_dir():
        raise ModelingError(f"不存在示例 {case}")
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, target, dirs_exist_ok=True)
    (target / "ai_usage.jsonl").touch(exist_ok=True)
    write_json(target / "state.json", {"schema_version": 1, "stages": {}, "created_at": now()})
    return target


def base_signature(root):
    p = load_problem(root)
    inputs = {"problem.json": sha(root / "problem.json"), p["data_file"]: sha(within(root, p["data_file"]))}
    extra_inputs = list(p.get("input_files", []))
    if (root / "raw").exists():
        extra_inputs += [f.relative_to(root).as_posix() for f in sorted((root / "raw").rglob("*")) if f.is_file()]
    for name in extra_inputs:
        file = within(root, name)
        if not file.is_file():
            raise ModelingError(f"附件不存在 {name}")
        inputs[name] = sha(file)
    for name in ["statement.md", "adapter.py"]:
        if (root / name).is_file():
            inputs[name] = sha(root / name)
    code = {f.name: sha(f) for f in Path(__file__).parent.glob("*.py")}
    return digest({"inputs": inputs, "code": code, "versions": versions()}), inputs


def stage_signature(stage, root, base, state, engine):
    upstream = {s: state["stages"].get(s, {}).get("signature") for s in STAGES[:STAGES.index(stage)]}
    extra = {}
    if stage in {"paper", "review"}:
        for path in [root / "paper/content.json", *sorted((ASSETS / "templates").glob("*"))]:
            extra[str(path.name)] = sha(path) if path.is_file() else "missing"
        extra["engine"] = engine
        log = root / "ai_usage.jsonl"
        extra["ai_usage"] = sha(log) if log.is_file() else "missing"
    return digest({"base": base, "stage": stage, "upstream": upstream, "extra": extra})


def output_valid(root, entry):
    for name, expected in entry.get("outputs", {}).items():
        file = within(root, name)
        if not file.is_file() or sha(file) != expected:
            return False
    return bool(entry.get("outputs"))


def status(path, engine=None):
    root = Path(path).resolve()
    state = read_json(root / "state.json")
    base, _ = base_signature(root)
    engine = engine or state.get("engine", "auto")
    valid_prefix = True
    result = {}
    for stage in STAGES:
        entry = state["stages"].get(stage, {})
        valid = valid_prefix and entry.get("status") == "complete" and entry.get("signature") == stage_signature(stage, root, base, state, engine) and output_valid(root, entry)
        result[stage] = "current" if valid else entry.get("status", "pending") if not entry or entry.get("status") == "failed" else "stale"
        valid_prefix = valid
    return {"workspace": str(root), "stages": result, "current": all(s == "current" for s in result.values())}


def validate_result_contract(result, p):
    if result.get("status") not in {"optimal", "computed", "limit_reached", "infeasible", "unbounded", "solver_error"}:
        raise ModelingError("适配器结果 status 非法")
    if not isinstance(result.get("metrics"), dict) or not result["metrics"]:
        raise ModelingError("结果必须有非空 metrics 对象")
    for key, val in result["metrics"].items():
        if val is not None:
            from .core import number
            number(val, f"metrics.{key}")
    if not isinstance(result.get("tables"), dict):
        raise ModelingError("结果必须有 tables 对象")
    for key, rows in result["tables"].items():
        if not key.replace("_", "").isalnum() or not isinstance(rows, list):
            raise ModelingError("数据表名只能包含字母、数字和下划线，表值必须是行列表")
        if rows and (not all(isinstance(x, dict) for x in rows) or any(set(x) != set(rows[0]) for x in rows)):
            raise ModelingError("数据表各行的列名必须一致")
    coverage = result.get("coverage", {})
    for q in p["questions"]:
        if coverage.get(q["id"]) != "computed" and result["status"] in {"optimal", "computed"}:
            raise ModelingError(f"适配器没有计算小问 {q['id']}，请补充实现或修正问题映射")


def execute_stage(stage, root, p, base, inputs, engine):
    def read(name):
        return read_json(root / name)
    if stage == "analyze":
        analysis = {"title": p["title"], "questions": p["questions"], "kind": p["kind"],
                    "given": {"data_origin": p["data_origin"], "units": p["units"]},
                    "assumptions": p["assumptions"], "unresolved": p.get("unresolved", []),
                    "note": "此记录来自队员或宿主 AI 对赛题的结构化解释，需对照原题审阅。"}
        if analysis["unresolved"]:
            raise ModelingError("problem.json 仍有 unresolved 条目，请明确影响计算的歧义后继续")
        write_json(root / "analysis.json", analysis)
        return ["analysis.json"]
    if stage == "data":
        d = models.prepare(p, root)
        write_json(root / "data/processed.json", d)
        write_json(root / "data/quality.json", d.get("quality", {"source": p["data_origin"]}))
        return ["data/processed.json", "data/quality.json"]
    d = read("data/processed.json")
    if stage == "model":
        m = models.model(p, d, root)
        for name in ["family", "variables", "equations", "assumptions", "limitations"]:
            if name not in m:
                raise ModelingError(f"模型说明缺少字段 {name}")
        write_json(root / "model.json", m)
        return ["model.json"]
    if stage == "solve":
        (root / "figures").mkdir(exist_ok=True)
        result = models.solve(p, d, root, root / "figures")
        validate_result_contract(result, p)
        result["result_id"] = base[:16]
        result["input_signature"] = base
        write_json(root / "solution.json", result)
        outputs = ["solution.json"]
        for name, rows in result["tables"].items():
            file = f"tables/{name}.csv"
            write_csv(root / file, rows)
            outputs.append(file)
        figures = create_figures(p, d, result, root)
        outputs += ["figures/manifest.json"]
        for f in figures:
            for key in ["path", "vector_path"]:
                if f.get(key):
                    file = within(root, f[key])
                    if not file.is_file():
                        raise ModelingError(f"适配器声明的图文件不存在 {f[key]}")
                    outputs.append(file.relative_to(root).as_posix())
        write_json(root / "provenance.json", {"result_id": result["result_id"], "input_signature": base,
                   "inputs": inputs, "versions": versions(), "generated_at": now(), "seed": p["options"].get("seed", 20261105),
                   "data_origin": p["data_origin"], "adapter": p["kind"], "algorithm_code": "math_modeling/models.py or workspace/adapter.py"})
        outputs.append("provenance.json")
        # Reproduction script uses the installed project, never an absolute development-machine path.
        (root / "reproduce.py").write_text("from pathlib import Path\nfrom math_modeling.pipeline import run\nrun(Path(__file__).resolve().parent, force=True)\n", encoding="utf-8")
        outputs.append("reproduce.py")
        # Preserve the exact implementation used for this result, alongside the full project source.
        snapshot = root / "code_snapshot"
        snapshot.mkdir(exist_ok=True)
        for source in sorted(Path(__file__).parent.glob("*.py")):
            shutil.copy2(source, snapshot / source.name)
            outputs.append(f"code_snapshot/{source.name}")
        if (root / "adapter.py").is_file():
            shutil.copy2(root / "adapter.py", snapshot / "adapter.py")
            outputs.append("code_snapshot/adapter.py")
        return outputs
    result = read("solution.json")
    if stage == "validate":
        v = models.validate(p, d, result, root)
        checks = v.get("checks", [])
        if not checks or any(not isinstance(c.get("passed"), bool) or not c.get("name") for c in checks):
            raise ModelingError("核验适配器必须返回非空、带布尔 passed 和 name 的 checks")
        v["passed"] = all(x["passed"] for x in checks)
        v["result_id"] = result["result_id"]
        write_json(root / "validation.json", v)
        write_csv(root / "checks.csv", [{"name": x["name"], "passed": x["passed"], "detail": json.dumps(x.get("detail"), ensure_ascii=False)} for x in checks])
        if not v["passed"]:
            raise ModelingError("计算核验失败，详见 validation.json；论文阶段未执行")
        return ["validation.json", "checks.csv"]
    if stage == "paper":
        return build(root, p, d, read("model.json"), result, read("validation.json"), engine)
    report = audit(root, check_state=False)
    write_json(root / "review.json", report)
    if not report["passed"]:
        raise ModelingError("论文审阅检查失败，详见 review.json")
    (root / "review.md").write_text("# 自动审阅报告\n\n" + "\n".join(f"- {x}" for x in report["notes"]+report["warnings"]+report["errors"]) + "\n", encoding="utf-8")
    return ["review.json", "review.md"]


def run(path, until="review", force=False, engine="auto", emit=print):
    root = Path(path).resolve()
    p = load_problem(root)
    if until not in STAGES:
        raise ModelingError(f"未知阶段 {until}")
    state = read_json(root / "state.json")
    base, inputs = base_signature(root)
    state["engine"] = engine
    rebuilding = force
    for stage in STAGES[:STAGES.index(until)+1]:
        entry = state["stages"].get(stage, {})
        signature = stage_signature(stage, root, base, state, engine)
        if not rebuilding and entry.get("status") == "complete" and entry.get("signature") == signature and output_valid(root, entry):
            emit(f"[cached] {stage}")
            continue
        rebuilding = True
        for later in STAGES[STAGES.index(stage)+1:]:
            if later in state["stages"]:
                state["stages"][later]["status"] = "stale"
        state["stages"][stage] = {"status": "running", "signature": signature, "started_at": now()}
        write_json(root / "state.json", state)
        try:
            outputs = execute_stage(stage, root, p, base, inputs, engine)
            state["stages"][stage].update({"status": "complete", "completed_at": now(), "outputs": {name: sha(within(root, name)) for name in outputs}})
            emit(f"[done] {stage}")
        except Exception as exc:
            state["stages"][stage].update({"status": "failed", "error": str(exc), "completed_at": now()})
            write_json(root / "state.json", state)
            raise
        write_json(root / "state.json", state)
    return state


def audit(path, check_state=True):
    root = Path(path).resolve()
    errors, warnings = [], []
    p = load_problem(root)
    result = read_json(root / "solution.json")
    v = read_json(root / "validation.json")
    base, _ = base_signature(root)
    if result.get("input_signature") != base:
        errors.append("输入、适配器或运行环境已变化，结果过期")
    if not v.get("passed") or v.get("result_id") != result.get("result_id"):
        errors.append("核验未通过或结果版本不一致")
    for claim in read_json(root / "paper/claims.json"):
        value = lookup(result["metrics"] if claim["kind"] == "metric" else p if claim["kind"] == "param" else result, claim["path"])
        if value != claim["value"] or claim["result_id"] != result["result_id"]:
            errors.append(f"论文数值绑定不一致: {claim['id']}")
    from .paper import render_content
    abstract, sections, current_claims, sources = render_content(read_json(root / "paper/content.json"), p, result)
    if current_claims != read_json(root / "paper/claims.json"):
        errors.append("论文内容已变化，尚未重新构建")
    manuscript = (root / "paper/manuscript.md").read_text(encoding="utf-8")
    if abstract not in manuscript or any(s["text"] not in manuscript for s in sections):
        errors.append("论文正文与绑定内容不一致")
    if check_state:
        s = status(root)
        for stage, value in s["stages"].items():
            if value != "current":
                errors.append(f"阶段 {stage} 状态为 {value}")
    pending = [x["id"] for x in sources if x.get("verification") != "human_verified"]
    if pending:
        warnings.append("需要队员打开并核验来源: " + ", ".join(pending))
    logs = root / "ai_usage.jsonl"
    if not logs.exists() or not logs.read_text(encoding="utf-8").strip():
        warnings.append("AI 使用记录为空；使用 AI 时请据实补充，空记录不能解释为未使用 AI")
    return {"passed": not errors, "draft": True, "result_id": result["result_id"], "errors": errors, "warnings": warnings,
            "notes": ["自动核验、数值绑定和产物一致性检查完成。", "模型假设、题意覆盖、来源支持与赛事格式需要队员审阅；本工具不自动提交论文。"]}


def log_ai(root, tool, purpose, human_review="", model="unspecified"):
    root = Path(root)
    load_problem(root)
    with (root / "ai_usage.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps({"timestamp": now(), "tool": tool, "model": model, "purpose": purpose, "human_review": human_review}, ensure_ascii=False)+"\n")
