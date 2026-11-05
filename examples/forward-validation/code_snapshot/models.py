"""Two reference adapters and a documented user-authored adapter protocol."""
from __future__ import annotations

from datetime import date, timedelta
import importlib.util
import itertools
import math
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp

from .core import ModelingError, csv_rows, integer, number, within


def custom_module(workspace):
    path = Path(workspace) / "adapter.py"
    if not path.is_file():
        raise ModelingError("custom 题型需要 adapter.py，见 docs/ADAPTERS.md")
    spec = importlib.util.spec_from_file_location("mm_user_adapter", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ["prepare", "model", "solve", "validate"]:
        if not callable(getattr(module, name, None)):
            raise ModelingError(f"adapter.py 缺少函数 {name}")
    return module


def prepare(p, workspace):
    rows = csv_rows(within(workspace, p["data_file"]))
    if p["kind"] == "custom":
        return custom_module(workspace).prepare(p, rows)
    if p["kind"] == "allocation":
        resources = p.get("resources", {})
        if not isinstance(resources, dict) or not resources:
            raise ModelingError("allocation 需要非空 resources 对象")
        for r, value in resources.items():
            number(value, f"capacity.{r}", 0)
            if r not in p["units"]:
                raise ModelingError(f"资源 {r} 缺少单位")
        names, profits, low, upper, matrix = [], [], [], [], []
        for row in rows:
            required = {"product", "profit", "min_units", "max_units", *resources}
            if not required <= row.keys():
                raise ModelingError(f"产品 CSV 缺少字段: {sorted(required - row.keys())}")
            name = row["product"].strip()
            if not name or name in names:
                raise ModelingError("产品名为空或重复")
            names.append(name)
            profits.append(number(row["profit"], f"{name}.profit"))
            lo = integer(row["min_units"], f"{name}.min_units", 0, 10**6)
            hi = integer(row["max_units"], f"{name}.max_units", 0, 10**6)
            if lo > hi:
                raise ModelingError(f"{name} 最低产量大于最高产量")
            low.append(lo)
            upper.append(hi)
            matrix.append([number(row[r], f"{name}.{r}", 0) for r in resources])
        return {"rows": len(rows), "names": names, "profits": profits,
                "lower": low, "upper": upper, "A": np.asarray(matrix).T.tolist(),
                "resources": list(resources), "capacity": list(map(float, resources.values())),
                "quality": {"missing_policy": "reject", "source": p["data_origin"], "units": p["units"]}}
    dates, y = [], []
    for row in rows:
        if not {"date", "value"} <= row.keys():
            raise ModelingError("forecast CSV 需要 date,value 列")
        try:
            d = date.fromisoformat(row["date"])
        except ValueError as exc:
            raise ModelingError("date 必须是 ISO 日期 YYYY-MM-DD") from exc
        if dates and d != dates[-1] + timedelta(days=1):
            raise ModelingError("日期必须严格递增、连续且不重复；请显式处理缺失日期")
        dates.append(d)
        y.append(number(row["value"], "value"))
    if len(y) < 42:
        raise ModelingError("参考预测适配器至少需要 42 个连续日观测")
    horizon = integer(p.get("horizon", 7), "horizon", 1, 90)
    holdout = integer(p.get("holdout", 14), "holdout", 7, len(y) // 3)
    return {"rows": len(y), "dates": [d.isoformat() for d in dates], "y": y,
            "horizon": horizon, "holdout": holdout,
            "quality": {"missing_policy": "reject", "source": p["data_origin"], "units": p["units"]}}


def model(p, d, workspace):
    if p["kind"] == "custom":
        return custom_module(workspace).model(p, d)
    if p["kind"] == "allocation":
        return {"family": "mixed-integer linear programming", "variables": [
            {"symbol": f"x_{i+1}", "meaning": n, "domain": "nonnegative integer", "unit": p["units"].get("quantity", "件")}
            for i, n in enumerate(d["names"])],
            "equations": [r"\max\; z=\sum_{j=1}^{n}p_jx_j",
                          r"\sum_{j=1}^{n}a_{ij}x_j\leq b_i\quad(i=1,\ldots,m)",
                          r"l_j\leq x_j\leq u_j,\quad x_j\in\mathbb{Z}_{\geq0}"],
            "baseline": "从最低产量出发，按单位归一化资源利润贪心增量配置；若最低产量不可行则报告不可行。",
            "selection": "决策变量是整数，目标和资源约束均线性；使用 MILP 并与线性松弛上界比较。",
            "assumptions": p["assumptions"],
            "limitations": ["利润与资源消耗视为常数，未包含价格反馈。", "情景扰动属于局部分析，不代表随机鲁棒最优。"]}
    return {"family": "time-ordered model comparison", "variables": [
        {"symbol": "t", "meaning": "自起始日期起的日序号", "domain": "integer", "unit": "日"},
        {"symbol": "y_t", "meaning": "日观测值", "domain": "real", "unit": p["units"].get("value", "单位")}],
        "equations": [r"\widehat y_t=\beta_0+\beta_1t",
                      r"\widehat y_t=\beta_0+\beta_1t+\beta_2\sin(2\pi t/7)+\beta_3\cos(2\pi t/7)",
                      r"\operatorname{RMSE}=\sqrt{N^{-1}\sum_t(y_t-\widehat y_t)^2}"],
        "baseline": "同星期朴素预测（仅使用预测起点之前最后一周的观测）。",
        "selection": "仅在最终测试集之前的数据上进行扩展窗口验证，按平均 RMSE 选择模型；测试集只评价一次。",
        "assumptions": p["assumptions"],
        "limitations": ["候选模型仅含周周期和线性趋势，结构突变会影响外推。", "结果是点预测；本案例未估计经校准的预测区间。"]}


def _optimize(d, capacity, time_limit, relaxed=False):
    r = milp(-np.asarray(d["profits"]), integrality=np.zeros(len(d["names"])) if relaxed else np.ones(len(d["names"])),
             bounds=Bounds(d["lower"], d["upper"]),
             constraints=LinearConstraint(np.asarray(d["A"]), -np.inf, capacity),
             options={"time_limit": time_limit, "mip_rel_gap": 0.0})
    status = {0: "optimal", 1: "limit_reached", 2: "infeasible", 3: "unbounded", 4: "solver_error"}.get(r.status, "solver_error")
    x = None if r.x is None else list(map(float, r.x))
    return {"status": status, "x": x, "objective": None if x is None else float(np.dot(d["profits"], x)),
            "gap": None if getattr(r, "mip_gap", None) is None else float(r.mip_gap), "message": r.message}


def _greedy(d):
    A, b, x = np.array(d["A"]), np.array(d["capacity"]), np.array(d["lower"], dtype=float)
    if np.any(A @ x > b + 1e-8):
        return None
    weights = (A / np.maximum(b, 1)[:, None]).sum(axis=0)
    order = np.argsort(-np.asarray(d["profits"]) / np.maximum(weights, 1e-12))
    for j in order:
        if d["profits"][j] <= 0:
            continue
        limits = [(b[i] - (A @ x)[i]) / A[i, j] for i in range(len(b)) if A[i, j] > 0]
        amount = max(0, min(d["upper"][j] - x[j], math.floor(min(limits) + 1e-8) if limits else d["upper"][j] - x[j]))
        x[j] += amount
    return float(np.dot(d["profits"], x))


def features(t, seasonal):
    t = np.asarray(t, dtype=float)
    columns = [np.ones_like(t), t]
    if seasonal:
        columns += [np.sin(2*np.pi*t/7), np.cos(2*np.pi*t/7)]
    return np.column_stack(columns)


def predict(name, y_train, start, count):
    if name == "seasonal_naive":
        return np.asarray([y_train[len(y_train)-7 + i % 7] for i in range(count)]), []
    seasonal = name == "trend_weekly"
    coeff, _, rank, _ = np.linalg.lstsq(features(np.arange(len(y_train)), seasonal), y_train, rcond=None)
    if rank < len(coeff):
        raise ModelingError("设计矩阵不满秩")
    return features(np.arange(start, start+count), seasonal) @ coeff, coeff.tolist()


def scores(actual, predicted):
    a, p = np.asarray(actual), np.asarray(predicted)
    return {"rmse": float(np.sqrt(np.mean((a-p)**2))), "mae": float(np.mean(np.abs(a-p)))}


def solve(p, d, workspace, output_dir):
    if p["kind"] == "custom":
        return custom_module(workspace).solve(p, d, output_dir)
    if p["kind"] == "allocation":
        limit = number(p["options"].get("time_limit", 30), "time_limit", .01, 3600)
        main = _optimize(d, d["capacity"], limit)
        relaxed = _optimize(d, d["capacity"], limit, True)
        baseline = _greedy(d)
        scenarios = []
        for factor in [.9, 1.0, 1.1]:
            r = main if factor == 1 else _optimize(d, (np.asarray(d["capacity"])*factor).tolist(), limit)
            scenarios.append({"capacity_factor": factor, "status": r["status"], "objective": r["objective"]})
        metrics = {"objective": main["objective"], "baseline_objective": baseline,
                   "relaxation_upper_bound": relaxed["objective"] if relaxed["status"] == "optimal" else None,
                   "improvement_percent": None if baseline in (None, 0) or main["objective"] is None else (main["objective"]-baseline)/abs(baseline)*100}
        allocations = [] if main["x"] is None else [{"product": n, "quantity": x, "profit": x*v}
            for n, x, v in zip(d["names"], main["x"], d["profits"])]
        return {"status": main["status"], "metrics": metrics, "solver": main,
                "tables": {"allocation": allocations, "sensitivity": scenarios},
                "coverage": {q["id"]: "computed" for q in p["questions"]}}
    y = np.asarray(d["y"])
    split = len(y)-d["holdout"]
    candidates = ["seasonal_naive", "trend", "trend_weekly"]
    folds, cv = [], {k: [] for k in candidates}
    fold_size = max(7, split//8)
    for end in [split-3*fold_size, split-2*fold_size, split-fold_size]:
        if end < 14:
            raise ModelingError("数据不足以构造训练内扩展窗口验证")
        folds.append({"train_start": 0, "train_end_exclusive": end, "valid_start": end, "valid_end_exclusive": end+fold_size})
        for name in candidates:
            pred, _ = predict(name, y[:end], end, fold_size)
            cv[name].append(scores(y[end:end+fold_size], pred)["rmse"])
    mean_cv = {k: float(np.mean(v)) for k, v in cv.items()}
    selected = min(candidates, key=lambda x: mean_cv[x])
    pred, coeff_test = predict(selected, y[:split], split, len(y)-split)
    naive, _ = predict("seasonal_naive", y[:split], split, len(y)-split)
    final, coeff = predict(selected, y, len(y), d["horizon"])
    holdout = [{"date": dt, "actual": float(a), "predicted": float(v), "baseline": float(b)}
        for dt, a, v, b in zip(d["dates"][split:], y[split:], pred, naive)]
    last = date.fromisoformat(d["dates"][-1])
    future = [{"date": (last+timedelta(days=i+1)).isoformat(), "predicted": float(v)} for i, v in enumerate(final)]
    m = scores(y[split:], pred)
    base = scores(y[split:], naive)
    return {"status": "computed", "selected_model": selected,
            "selected_model_name": {"seasonal_naive": "周朴素模型", "trend": "线性趋势模型", "trend_weekly": "趋势与周周期模型"}[selected],
            "metrics": {"holdout_rmse": m["rmse"], "holdout_mae": m["mae"], "baseline_rmse": base["rmse"],
                        "rmse_improvement_percent": None if base["rmse"] == 0 else (base["rmse"]-m["rmse"])/base["rmse"]*100,
                        "forecast_total": float(sum(final)), "observations": len(y), "holdout_size": len(pred)},
            "test_coefficients": coeff_test, "final_coefficients": coeff, "split_index": split,
            "cv_folds": folds, "cv_scores": mean_cv, "cv_fold_scores": cv,
            "tables": {"holdout": holdout, "forecast": future,
                       "model_comparison": [{"model": name, "cv_rmse": mean_cv[name]} for name in candidates]},
            "coverage": {q["id"]: "computed" for q in p["questions"]}}


def validate(p, d, r, workspace):
    if p["kind"] == "custom":
        return custom_module(workspace).validate(p, d, r)
    checks = []
    def check(name, passed, detail):
        checks.append({"name": name, "passed": bool(passed), "detail": detail})
    if p["kind"] == "allocation":
        x = r["solver"]["x"]
        if x is None:
            check("solution_available", False, r["status"])
        else:
            x, A, b = np.array(x), np.array(d["A"]), np.array(d["capacity"])
            check("bounds", np.all(x >= np.array(d["lower"])-1e-7) and np.all(x <= np.array(d["upper"])+1e-7), "逐项检查变量上下界")
            check("integrality", np.allclose(x, np.round(x), atol=1e-7, rtol=0), "逐项检查整数域")
            for name, used, cap in zip(d["resources"], A@x, b):
                check(f"capacity:{name}", used <= cap+1e-7, {"used": float(used), "capacity": float(cap)})
            recomputed = sum(v*profit for v, profit in zip(x, d["profits"]))
            check("objective_recomputed", math.isclose(recomputed, r["metrics"]["objective"], rel_tol=1e-9, abs_tol=1e-7), recomputed)
            bound = r["metrics"]["relaxation_upper_bound"]
            if bound is not None:
                check("relaxation_bound", recomputed <= bound+1e-7, bound)
            states = math.prod(hi-lo+1 for lo, hi in zip(d["lower"], d["upper"]))
            if states <= 200000:
                best = -math.inf
                for candidate in itertools.product(*(range(lo, hi+1) for lo, hi in zip(d["lower"], d["upper"]))):
                    if all(sum(A[i,j]*candidate[j] for j in range(len(candidate))) <= b[i]+1e-8 for i in range(len(b))):
                        best = max(best, sum(v*profit for v, profit in zip(candidate, d["profits"])))
                # Only an optimal status claims equality; a time-limited feasible point need not be optimal.
                check("enumeration_reference", recomputed <= best+1e-7 and (r["status"] != "optimal" or abs(recomputed-best)<1e-7), {"states": states, "best": best})
    else:
        split = r["split_index"]
        check("chronological_split", split == len(d["y"])-d["holdout"], {"split": split, "n": len(d["y"])})
        for i, fold in enumerate(r["cv_folds"]):
            check(f"no_leakage_fold_{i}", 14 <= fold["train_end_exclusive"] == fold["valid_start"] < fold["valid_end_exclusive"] <= split, fold)
        check("selection_from_training_cv", r["selected_model"] == min(r["cv_scores"], key=r["cv_scores"].get), r["cv_scores"])
        rows = r["tables"]["holdout"]
        check("holdout_dates", [x["date"] for x in rows] == d["dates"][split:], "测试集日期与原始数据一致")
        check("holdout_actuals", [x["actual"] for x in rows] == d["y"][split:], "测试观测与原始数据一致")
        error_sq = [(x["actual"]-x["predicted"])**2 for x in rows]
        rmse = math.sqrt(sum(error_sq)/len(error_sq))
        check("rmse_recomputed", math.isclose(rmse, r["metrics"]["holdout_rmse"], rel_tol=1e-10, abs_tol=1e-10), rmse)
        # Independently reconstruct the fit using the normal equations (small reference design).
        if r["selected_model"] != "seasonal_naive":
            X = features(np.arange(split), r["selected_model"] == "trend_weekly")
            beta = np.linalg.solve(X.T@X, X.T@np.array(d["y"][:split]))
            predicted = features(np.arange(split, len(d["y"])), r["selected_model"] == "trend_weekly") @ beta
            check("independent_fit", np.allclose(predicted, [x["predicted"] for x in rows], atol=1e-6), "正规方程与最小二乘求解交叉核对")
        future = r["tables"]["forecast"]
        check("horizon", len(future) == d["horizon"], len(future))
        expected_dates = [(date.fromisoformat(d["dates"][-1])+timedelta(days=i+1)).isoformat() for i in range(d["horizon"])]
        check("future_dates", [x["date"] for x in future] == expected_dates, expected_dates)
        check("finite_predictions", all(math.isfinite(x["predicted"]) for x in future), "有限数值检查")
    return {"passed": bool(checks) and all(x["passed"] for x in checks), "checks": checks,
            "scope": "自动核验覆盖已编码条件；题意解释与模型假设仍需队员审阅。"}
