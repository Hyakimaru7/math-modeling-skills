from __future__ import annotations

import os
from pathlib import Path

from .core import write_json


def create_figures(problem, data, result, workspace):
    root = Path(workspace)
    os.environ.setdefault("MPLCONFIGDIR", str(root / ".cache" / "matplotlib"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    target = root / "figures"
    target.mkdir(exist_ok=True)
    figures = []
    def save(fig, name, caption, inputs):
        for suffix in ["png", "pdf"]:
            fig.savefig(target / f"{name}.{suffix}", dpi=220, facecolor="white")
        plt.close(fig)
        figures.append({"path": f"figures/{name}.png", "vector_path": f"figures/{name}.pdf", "caption": caption,
                        "data": inputs, "result_id": result["result_id"], "uncertainty": "none; point estimates"})
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                         "grid.alpha": .2, "figure.figsize": (7, 3.5), "savefig.bbox": None}):
        if problem["kind"] == "allocation":
            rows = result["tables"]["allocation"]
            if rows:
                fig, ax = plt.subplots(layout="constrained")
                ax.bar([f"P{i+1}" for i in range(len(rows))], [x["quantity"] for x in rows], color="#0072B2", hatch="//", edgecolor="white")
                ax.set(xlabel="Product (order follows allocation table)", ylabel="Quantity (units)", ylim=(0, None))
                save(fig, "allocation", "各产品的整数配置数量；产品顺序与配置表一致。", ["tables/allocation.csv"])
            rows = [x for x in result["tables"]["sensitivity"] if x["objective"] is not None]
            if rows:
                fig, ax = plt.subplots(layout="constrained")
                ax.plot([x["capacity_factor"] for x in rows], [x["objective"] for x in rows], "o-", color="#0072B2")
                ax.set(xlabel="Common capacity multiplier", ylabel="Objective value (profit units)")
                save(fig, "sensitivity", "全部资源容量同步变化时的目标值；不可行情景不绘制数值。", ["tables/sensitivity.csv"])
        elif problem["kind"] == "forecast":
            rows = result["tables"]["holdout"]
            fig, ax = plt.subplots(layout="constrained")
            t = list(range(len(rows)))
            ax.plot(t, [x["actual"] for x in rows], "o-", label="Observed", color="#333333", markersize=4)
            ax.plot(t, [x["predicted"] for x in rows], "s--", label="Selected model", color="#0072B2", markersize=4)
            ax.plot(t, [x["baseline"] for x in rows], "^:", label="Weekly naive", color="#D55E00", markersize=4)
            ax.set(xlabel="Holdout day index", ylabel="Daily value (original units)")
            ax.legend(frameon=False)
            save(fig, "holdout", "最终留出测试集上的实际值、所选模型与周朴素基线预测。", ["tables/holdout.csv"])
            future = result["tables"]["forecast"]
            fig, ax = plt.subplots(layout="constrained")
            start = max(0, len(data["y"])-28)
            ax.plot(range(start, len(data["y"])), data["y"][start:], "o-", label="Observed", color="#333333", markersize=3)
            ax.plot(range(len(data["y"]), len(data["y"])+len(future)), [x["predicted"] for x in future], "s--", label="Future point forecast", color="#0072B2", markersize=4)
            ax.axvline(len(data["y"])-.5, color="#777777", linestyle=":")
            ax.set(xlabel="Day index from start", ylabel="Daily value (original units)")
            ax.legend(frameon=False)
            save(fig, "forecast", "使用全部已观测数据重新拟合后的未来点预测；竖线右侧为外推区间。", ["data/processed.json", "tables/forecast.csv"])
        else:
            for f in result.get("figures", []):
                figures.append(f)
    write_json(target / "manifest.json", figures)
    return figures
