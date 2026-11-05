from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys

from .core import ModelingError, versions


def main(argv=None):
    parser = argparse.ArgumentParser(prog="mm", description="数学建模：模型、代码、结果核验与论文构建")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="创建独立案例工作区")
    init.add_argument("workspace")
    init.add_argument("--case", choices=["allocation", "forecast", "custom"], default="allocation")
    run = sub.add_parser("run", help="按依赖执行；当前产物自动复用，变更或损坏产物自动重建")
    run.add_argument("workspace")
    run.add_argument("--until", choices=["analyze", "data", "model", "solve", "validate", "paper", "review"], default="review")
    run.add_argument("--force", action="store_true")
    run.add_argument("--engine", choices=["auto", "xelatex", "reportlab"], default="auto")
    for command in ["status", "audit"]:
        s = sub.add_parser(command)
        s.add_argument("workspace")
    ai = sub.add_parser("log-ai", help="记录实际发生的 AI 使用与人工核验")
    ai.add_argument("workspace")
    ai.add_argument("--tool", required=True)
    ai.add_argument("--purpose", required=True)
    ai.add_argument("--model", default="unspecified")
    ai.add_argument("--human-review", default="")
    sub.add_parser("doctor", help="检查 Python 依赖与 PDF 工具")
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            required = ["numpy", "scipy", "matplotlib", "jinja2", "reportlab", "pypdf"]
            found = {name: importlib.util.find_spec(name) is not None for name in required}
            print(json.dumps({"dependencies": found, "tools": {name: shutil.which(name) for name in ["xelatex", "pdftoppm"]}, "versions": versions(),
                              "pdf": "XeLaTeX 中文论文；无 TeX 时可用 ReportLab 便携预览"}, ensure_ascii=False, indent=2))
            return 0 if all(found.values()) else 2
        from . import pipeline
        if args.command == "init":
            print(pipeline.init_workspace(args.workspace, args.case))
        elif args.command == "run":
            pipeline.run(args.workspace, args.until, args.force, args.engine)
        elif args.command == "status":
            report = pipeline.status(args.workspace)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["current"] else 1
        elif args.command == "audit":
            report = pipeline.audit(args.workspace)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report["passed"] else 2
        else:
            pipeline.log_ai(Path(args.workspace), args.tool, args.purpose, args.human_review, args.model)
            print("使用记录已追加；重新运行以更新论文审阅记录。")
        return 0
    except (ModelingError, OSError, KeyError, ValueError) as exc:
        print(f"mm: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
