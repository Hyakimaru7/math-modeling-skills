# 工作区协议

本包由八个 skills 与 math-modeling-skills Python 运行器组成，应一起分发。用户已给定的题目、工具、语言和交付范围优先。

## 输入

- problem.json：schema_version=1；kind 为 allocation、forecast 或 custom；title、data_file、data_origin、units、questions、assumptions 为必要字段。
- questions：每项含唯一 id、text、depends_on；内置题型还需 task。allocation 支持 allocation/sensitivity；forecast 支持 comparison/forecast。依赖图必须无环。
- options：seed 为非负整数，time_limit 为每次内置优化求解的秒上限。自定义算法自行实现预算。
- contest：profile、year、language、max_pages。内置模板为中文训练模板；填写其他语言不自动翻译或切换格式。必须由宿主按实际要求修改模板。
- sources：id、title、url、accessed、verification。状态为 unverified、opened_by_agent、human_verified；后者附人工核验人和日期。
- unresolved：影响计算的未决事项；非空时分析阶段停止，给出明确提示。
- 原始附件放 raw/，其余使用文件放 input_files。所有这些文件均进入指纹。
- statement.md 保存题意解释和定位；custom 还包含 adapter.py。
- paper/content.json 为人工或宿主 AI 撰写的正文模板，使用绑定标记引用结果。

## 状态

流程为 analyze → data → model → solve → validate → paper → review。state.json 保存输入签名、阶段状态和产物哈希。相同输入复用完整产物；变化、删除或改写产物会触发从受影响阶段向后重建。运行器源码和依赖版本改变会保守失效全部计算阶段，正文修改仅影响 paper/review。

run 执行确定性任务，不包含隐藏的模型 API；自然语言推理、检索、适配器编写和正文撰写由宿主通过 skills 完成。

## 输出与证据

analysis.json、data/processed.json、model.json、solution.json、validation.json、checks.csv、tables/、figures/、provenance.json、paper/、review.json。

solution.metrics 为标量数值或明确的 null，tables 为一致列名的行列表。coverage 仅标记实际已计算的小问。没有解或没有验证结果时，不编造有效指标，不构建“已完成”论文。

所有论文保持 draft；通过自动检查不等同于人工科学核验、赛事合规或获奖承诺。