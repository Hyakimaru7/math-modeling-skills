from __future__ import annotations

import math
import re
import shutil
import subprocess
from pathlib import Path

from .core import ModelingError, read_json, within, write_json

TOKEN = re.compile(r"\{\{(metric|value|param|cite):([A-Za-z0-9_.-]+)(?:\|([^{}]+))?\}\}")


def latex_escape(text):
    escapes = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(escapes.get(c, c) for c in str(text))


def lookup(value, path):
    try:
        for key in path.split("."):
            value = value[key]
        return value
    except (KeyError, TypeError) as exc:
        raise ModelingError(f"论文引用了不存在的结果字段 {path}") from exc


def render_content(content, p, result):
    sources = {s["id"]: s for s in p.get("sources", [])}
    claims, used = [], set()
    def render(text, section):
        # Literal numbers in prose must be bound to a result, including dates and sample counts.
        cleaned = TOKEN.sub("", text)
        if re.search(r"\d", cleaned):
            raise ModelingError(f"{section} 存在未绑定数字；请使用 metric/value 标记引用结果或将给定条件放入模型说明")
        def replace(match):
            kind, path, fmt = match.groups()
            if kind == "cite":
                if path not in sources:
                    raise ModelingError(f"引用来源不存在: {path}")
                used.add(path)
                return f"[{path}]"
            value = lookup(result["metrics"] if kind == "metric" else p if kind == "param" else result, path)
            if value is None:
                raise ModelingError(f"论文引用的结果尚不可用: {path}")
            if kind == "metric" or fmt:
                if not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise ModelingError(f"metric 必须引用有限数值: {path}")
                try:
                    rendered = format(value, fmt or ".4g")
                except (ValueError, TypeError) as exc:
                    raise ModelingError(f"非法数值格式: {fmt}") from exc
            else:
                if isinstance(value, (dict, list)):
                    raise ModelingError("value 只能引用标量")
                rendered = str(value)
            claims.append({"id": f"C{len(claims)+1:03d}", "section": section, "kind": kind, "path": path,
                           "format": fmt, "value": value, "rendered": rendered, "result_id": result["result_id"]})
            return rendered
        output = TOKEN.sub(replace, text)
        if "{{" in output or "}}" in output:
            raise ModelingError(f"{section} 含有无法解析的绑定标记")
        return output
    if not isinstance(content.get("sections"), list) or not content.get("abstract"):
        raise ModelingError("paper/content.json 需要 abstract 和 sections")
    abstract = render(content["abstract"], "摘要")
    sections = []
    for s in content["sections"]:
        sections.append({"heading": s["heading"], "text": render(s["text"], s["heading"]), "question_ids": s.get("question_ids", [])})
    covered = {q for s in sections for q in s["question_ids"]}
    missing = {q["id"] for q in p["questions"]} - covered
    if missing:
        raise ModelingError(f"论文没有对应章节的小问: {sorted(missing)}")
    return abstract, sections, claims, [sources[x] for x in sorted(used)]


def format_cell(v):
    if v is None:
        return "不可用"
    return format(0.0 if abs(v) < 1e-12 else v, ".5g") if isinstance(v, float) else str(v)


def build(workspace, problem, data, model, result, validation, engine="auto"):
    root = Path(workspace)
    dest = root / "paper"
    dest.mkdir(exist_ok=True)
    if not validation.get("passed"):
        raise ModelingError("结果核验未通过，保留已有草稿并先修复计算")
    content = read_json(dest / "content.json")
    abstract, sections, claims, sources = render_content(content, problem, result)
    figures = read_json(root / "figures/manifest.json")
    for f in figures:
        if not within(root, f["path"]).is_file():
            raise ModelingError(f"图文件缺失 {f['path']}")
    tables = []
    table_names = {"allocation": "生产配置方案", "sensitivity": "资源容量情景", "holdout": "留出测试集逐日比较", "forecast": "未来逐日点预测", "model_comparison": "训练期扩展窗口比较", "estimate": "中心估计结果"}
    column_names = {"product": "产品", "quantity": "数量", "profit": "利润", "capacity_factor": "容量倍率", "status": "求解状态", "objective": "目标值", "date": "日期", "actual": "观测值", "predicted": "预测值", "baseline": "基线值", "model": "候选模型", "cv_rmse": "验证 RMSE", "center": "中心值", "count": "观测数"}
    labels = {"seasonal_naive": "周朴素模型", "trend": "线性趋势模型", "trend_weekly": "趋势与周周期模型", "optimal": "最优", "computed": "已计算", "limit_reached": "达到限制", "infeasible": "不可行", "unbounded": "无界", "solver_error": "求解错误"}
    for name, rows in result.get("tables", {}).items():
        if rows:
            tables.append({"name": table_names.get(name, name), "columns": [column_names.get(k, k) for k in rows[0]],
                           "rows": [[labels.get(str(row[k]), format_cell(row[k])) if k in {"model", "status"} else format_cell(row[k]) for k in rows[0]] for row in rows]})
    context = {"title": problem["title"], "abstract": abstract, "keywords": content.get("keywords", []),
               "sections": sections, "problem": problem, "model": model, "tables": tables,
               "figures": figures, "sources": sources, "result_id": result["result_id"], "validation": validation}
    md = [f"# {problem['title']}", "> 训练论文草稿 · 计算已核验，模型解释与引用待队员审阅。", "## 摘要", abstract,
          "关键词：" + "；".join(content.get("keywords", [])), "## 题目要求与数据来源", problem["data_origin"]]
    md += [f"- {q['id']}：{q['text']}" for q in problem["questions"]]
    md += ["## 建模假设"] + [f"- {x}" for x in problem["assumptions"]]
    md += ["## 模型表述", model.get("selection", ""), *[f"$$ {e} $$" for e in model.get("equations", [])]]
    for s in sections:
        md += [f"## {s['heading']}", s["text"]]
    for t in tables:
        md += [f"## 数据表：{t['name']}", "| " + " | ".join(t["columns"]) + " |", "|" + "---|"*len(t["columns"])]
        md += ["| " + " | ".join(row) + " |" for row in t["rows"]]
    for f in figures:
        md += [f"![{f['caption']}](../{f['path']})"]
    md += ["## 局限性"] + [f"- {x}" for x in model.get("limitations", [])]
    md += ["## 参考来源"] + [f"- [{s['id']}] {s['title']} — {s['url']}；核验状态：{s.get('verification', 'unverified')}" for s in sources]
    md += ["## 复现与使用说明", "在工作区所在项目中执行 `mm run <工作区> --force`，重新计算并构建论文。",
           "本文使用项目内声明的训练数据，不应将演示结论直接解释为实际业务结论。",
           f"结果记录：{result['result_id']}。实际 AI 使用记录见 ai_usage.jsonl；作者需据实补充人工修改和核验过程。"]
    (dest / "manuscript.md").write_text("\n\n".join(md)+"\n", encoding="utf-8")
    write_json(dest / "claims.json", claims)
    write_json(dest / "context.json", context)
    from jinja2 import Environment, FileSystemLoader, StrictUndefined
    templates = Path(__file__).parent / "assets/templates"
    env = Environment(loader=FileSystemLoader(templates), undefined=StrictUndefined,
                      block_start_string="((*", block_end_string="*))", variable_start_string="(((", variable_end_string=")))", autoescape=False)
    env.filters["tex"] = latex_escape
    tex = env.get_template("paper.tex.j2").render(**context)
    (dest / "paper.tex").write_text(tex, encoding="utf-8")
    if engine == "auto":
        engine = "xelatex" if shutil.which("xelatex") else "reportlab"
    if engine == "xelatex":
        exe = shutil.which("xelatex")
        if not exe:
            raise ModelingError("找不到 xelatex；安装 TeX Live/MiKTeX 或选择 --engine reportlab")
        command = [exe, "-no-shell-escape", "-halt-on-error", "-interaction=nonstopmode", "paper.tex"]
        logs = []
        for _ in range(2):
            try:
                proc = subprocess.run(command, cwd=dest, capture_output=True, text=True, timeout=90)
            except subprocess.TimeoutExpired as exc:
                raise ModelingError("XeLaTeX 编译超时；检查模板和 paper.tex") from exc
            logs.append(proc.stdout + proc.stderr)
            (dest / "build.log").write_text("\n".join(logs), encoding="utf-8")
            if proc.returncode:
                raise ModelingError("XeLaTeX 编译失败，详见 paper/build.log；没有使用旧 PDF 充当新结果")
    elif engine == "reportlab":
        build_preview(dest, context, root)
        (dest / "build.log").write_text("ReportLab portable preview; LaTeX source retained.\n", encoding="utf-8")
    else:
        raise ModelingError(f"未知 PDF 引擎 {engine}")
    from pypdf import PdfReader
    reader = PdfReader(dest / "paper.pdf")
    maximum = problem.get("contest", {}).get("max_pages")
    if maximum is not None and len(reader.pages) > int(maximum):
        raise ModelingError(f"PDF 共 {len(reader.pages)} 页，超过配置上限 {maximum}")
    write_json(dest / "build.json", {"engine": engine, "pages": len(reader.pages), "draft": True, "result_id": result["result_id"],
                                      "source_verification_pending": [s["id"] for s in sources if s.get("verification") != "human_verified"]})
    return ["paper/manuscript.md", "paper/claims.json", "paper/context.json", "paper/paper.tex", "paper/paper.pdf", "paper/build.json"]


def build_preview(dest, c, root):
    """Portable preview when no TeX installation is available; not a contest layout claim."""
    from xml.sax.saxutils import escape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Chinese", fontName="STSong-Light", fontSize=10.5, leading=17, spaceAfter=8, wordWrap="CJK"))
    styles.add(ParagraphStyle("ChineseHeading", fontName="STSong-Light", fontSize=14, leading=20, spaceBefore=14, spaceAfter=8))
    story = []
    def para(text, heading=False):
        story.append(Paragraph(escape(str(text)), styles["ChineseHeading" if heading else "Chinese"]))
    para(c["title"], True)
    para("训练论文草稿 / 便携预览排版；正式排版请使用 XeLaTeX。")
    para("摘要", True)
    para(c["abstract"])
    para("题目与数据", True)
    para(c["problem"]["data_origin"])
    for q in c["problem"]["questions"]:
        para(q["id"]+"："+q["text"])
    para("建模假设", True)
    for a in c["problem"]["assumptions"]:
        para(a)
    para("模型", True)
    para(c["model"].get("selection", ""))
    for e in c["model"].get("equations", []):
        para(e)
    for s in c["sections"]:
        para(s["heading"], True)
        para(s["text"])
    for t in c["tables"]:
        para(t["name"], True)
        rows = [[Paragraph(escape(x), styles["Chinese"]) for x in t["columns"]]]
        rows += [[Paragraph(escape(x), styles["Chinese"]) for x in row] for row in t["rows"]]
        table = Table(rows, colWidths=[470/len(t["columns"])]*len(t["columns"]), repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EAF1F5")), ("VALIGN", (0,0), (-1,-1), "TOP"), ("LINEBELOW", (0,0), (-1,0), .6, colors.grey)]))
        story += [table, Spacer(1, 10)]
    for f in c["figures"]:
        story.append(Image(str(within(root, f["path"])), width=470, height=235, kind="proportional"))
        para(f["caption"])
    para("局限性", True)
    for x in c["model"].get("limitations", []):
        para(x)
    para("参考来源", True)
    for s in c["sources"]:
        para(f"[{s['id']}] {s['title']} / {s['url']}")
    def footer(canvas, doc):
        canvas.setFont("STSong-Light", 8)
        canvas.drawString(42, 28, "训练论文草稿 · 需要人工审阅")
        canvas.drawRightString(552, 28, str(doc.page))
    SimpleDocTemplate(str(dest / "paper.pdf"), pagesize=(595,842), rightMargin=55, leftMargin=55, topMargin=45, bottomMargin=45).build(story, onFirstPage=footer, onLaterPages=footer)
