from __future__ import annotations

import csv
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlsplit

from . import __version__


class ModelingError(ValueError):
    """An actionable input, verification, or build error."""


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False)


def read_json(path):
    def invalid(x):
        raise ModelingError(f"非有限 JSON 数值: {x}")
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"), parse_constant=invalid)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelingError(f"无法读取 {path}: {exc}") from exc


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    fd, tmp = tempfile.mkstemp(prefix=".mm-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def within(root, name):
    root = Path(root).resolve()
    target = (root / name).resolve()
    if not target.is_relative_to(root):
        raise ModelingError(f"路径越出工作区: {name}")
    return target


def number(value, name, minimum=None, maximum=None):
    if isinstance(value, bool):
        raise ModelingError(f"{name} 不能是布尔值")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ModelingError(f"{name} 必须是数值") from exc
    if not math.isfinite(x):
        raise ModelingError(f"{name} 必须是有限数值")
    if minimum is not None and x < minimum:
        raise ModelingError(f"{name} 小于允许下限 {minimum}")
    if maximum is not None and x > maximum:
        raise ModelingError(f"{name} 大于允许上限 {maximum}")
    return x


def integer(value, name, minimum=1, maximum=10000):
    x = number(value, name, minimum, maximum)
    if x != int(x):
        raise ModelingError(f"{name} 必须是整数")
    return int(x)


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ModelingError("CSV 表头缺失或重复")
        rows = list(reader)
    if not rows or any(None in row for row in rows):
        raise ModelingError("CSV 无数据或列数不一致")
    return rows


def write_csv(path, rows):
    rows = list(rows)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)


def versions():
    result = {"python": platform.python_version(), "math-modeling-skills": __version__}
    for name in ["numpy", "scipy", "matplotlib", "Jinja2", "reportlab", "pypdf"]:
        try:
            result[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            result[name] = "unavailable"
    return result


def load_problem(workspace):
    p = read_json(Path(workspace) / "problem.json")
    if not isinstance(p, dict):
        raise ModelingError("problem.json 顶层必须是对象")
    if p.get("schema_version") != 1:
        raise ModelingError("problem.json 的 schema_version 必须为 1")
    if p.get("kind") not in {"allocation", "forecast", "custom"}:
        raise ModelingError("kind 必须为 allocation、forecast 或 custom；新模型请使用 custom 适配器")
    for key in ["title", "data_file", "data_origin", "questions", "assumptions", "units"]:
        if key not in p or not p[key]:
            raise ModelingError(f"problem.json 缺少必要字段 {key}")
    if not isinstance(p["questions"], list) or not isinstance(p["assumptions"], list):
        raise ModelingError("questions 和 assumptions 必须是列表")
    ids = [q.get("id") for q in p["questions"]]
    if None in ids or len(ids) != len(set(ids)):
        raise ModelingError("每个小问必须有唯一 id")
    for q in p["questions"]:
        if not q.get("text"):
            raise ModelingError("每个小问需要 text")
        if any(d not in ids or d == q["id"] for d in q.get("depends_on", [])):
            raise ModelingError("小问依赖不存在或指向自身")
        tasks = {"allocation": {"allocation", "sensitivity"}, "forecast": {"comparison", "forecast"}}
        if p["kind"] in tasks and q.get("task") not in tasks[p["kind"]]:
            raise ModelingError(f"内置 {p['kind']} 适配器不支持小问任务 {q.get('task')}；新任务请用 custom 实现")
    pending = {q["id"]: set(q.get("depends_on", [])) for q in p["questions"]}
    done = set()
    while pending:
        ready = {k for k, deps in pending.items() if deps <= done}
        if not ready:
            raise ModelingError("小问依赖存在环")
        done |= ready
        pending = {k: v for k, v in pending.items() if k not in ready}
    raw = within(workspace, p["data_file"])
    if not raw.is_file():
        raise ModelingError(f"找不到数据文件 {p['data_file']}")
    opts = p.setdefault("options", {})
    integer(opts.get("seed", 20261105), "seed", 0, 2**32 - 1)
    number(opts.get("time_limit", 30), "time_limit", 0.01, 3600)
    if not isinstance(p.get("sources", []), list):
        raise ModelingError("sources 必须是列表")
    source_ids = [s.get("id") for s in p.get("sources", [])]
    if None in source_ids or len(source_ids) != len(set(source_ids)):
        raise ModelingError("来源 id 缺失或重复")
    for s in p.get("sources", []):
        if not s.get("title") or urlsplit(s.get("url", "")).scheme not in {"http", "https"}:
            raise ModelingError("来源需要真实 title 和 http/https URL")
        verification = s.get("verification", "unverified")
        if verification not in {"unverified", "opened_by_agent", "human_verified"}:
            raise ModelingError("来源 verification 状态非法")
        if verification == "human_verified" and (not s.get("verifier") or not s.get("verified_at")):
            raise ModelingError("human_verified 需要实际核验人 verifier 和日期 verified_at")
        if any(c in s["url"] for c in ["{", "}", "\\", "\n", "\r"]):
            raise ModelingError("来源 URL 含不支持的控制字符")
    maximum = p.get("contest", {}).get("max_pages")
    if maximum is not None:
        integer(maximum, "contest.max_pages", 1, 1000)
    return p
