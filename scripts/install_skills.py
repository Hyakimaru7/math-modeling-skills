#!/usr/bin/env python3
"""Copy the complete skill bundle into an explicitly selected project."""
import argparse
from pathlib import Path
import shutil

parser = argparse.ArgumentParser()
parser.add_argument("--target", required=True, type=Path, help="目标项目 .agents/skills 路径")
parser.add_argument("--replace", action="store_true", help="显式替换本包同名 skills")
args = parser.parse_args()
source = Path(__file__).resolve().parents[1] / ".agents/skills"
target = args.target.expanduser().resolve()
if target == source.resolve():
    parser.error("目标就是当前 skills 目录，无需复制")
folders = sorted(p for p in source.iterdir() if p.is_dir())
conflicts = [p.name for p in folders if (target / p.name).exists()]
if conflicts and not args.replace:
    parser.error("同名 skills 已存在；需要替换时显式使用 --replace："+", ".join(conflicts))
for folder in folders:
    dest = target / folder.name
    if dest.is_symlink() or (dest.exists() and not dest.is_dir()):
        parser.error(f"目标不是普通目录，停止替换 {dest}")
target.mkdir(parents=True, exist_ok=True)
for folder in folders:
    dest = target / folder.name
    if dest.exists():
        if dest.is_symlink() or not dest.is_dir():
            parser.error(f"目标不是普通目录，停止替换 {dest}")
        shutil.rmtree(dest)
    shutil.copytree(folder, dest)
print(f"已复制 {len(folders)} 个 skills 到 {target}；请确保当前 Python 环境已安装项目运行器。")
