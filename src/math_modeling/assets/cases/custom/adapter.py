"""Runnable custom adapter; replace these four functions for a new contest model."""
from math_modeling.core import number

def prepare(problem, rows):
    values = [number(r["value"], "value") for r in rows]
    return {"values": values, "rows": len(values), "quality": {"source": problem["data_origin"]}}

def model(problem, data):
    return {"family": "quadratic loss", "variables": [{"symbol": "c", "meaning": "中心值", "unit": "单位", "domain": "real"}],
            "equations": [r"\min_c L(c)=\sum_i(y_i-c)^2"], "assumptions": problem["assumptions"],
            "selection": "等权平方损失是严格凸函数，样本均值给出唯一极小值。", "baseline": "任意固定中心。",
            "limitations": ["平方损失对离群值敏感。"]}

def solve(problem, data, output_dir):
    values = data["values"]
    center = sum(values)/len(values)
    return {"status": "optimal", "metrics": {"center": center, "loss": sum((x-center)**2 for x in values)},
            "tables": {"estimate": [{"center": center, "count": len(values)}]}, "coverage": {"Q1": "computed"}}

def validate(problem, data, result):
    c = result["metrics"]["center"]
    gradient = sum(2*(c-x) for x in data["values"])
    loss = lambda v: sum((x-v)**2 for x in data["values"])
    checks = [{"name": "stationarity", "passed": abs(gradient)<1e-10, "detail": gradient},
              {"name": "loss_recomputed", "passed": abs(loss(c)-result["metrics"]["loss"])<1e-10, "detail": loss(c)},
              {"name": "local_perturbation", "passed": loss(c-.01)>loss(c) and loss(c+.01)>loss(c), "detail": "双侧扰动"}]
    return {"passed": all(x["passed"] for x in checks), "checks": checks}
