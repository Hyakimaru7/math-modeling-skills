---
name: mm-analyze
description: "将数学建模赛题和附件解释为结构化问题、小问依赖、给定条件与假设。用于建模前的题意分析及已有模型与原题对照。"
---

先阅读原题及附件说明，保留页码、题号、字段来源。输出结构化的问题解释，不把算法名称当作建模目标。

## 步骤

- 列出各小问的目标、需要回答的量、交付形式以及上下游关系。问题之间共享的数据、预测值和参数写明版本及单位。
- 区分原题给定、数据推断、额外假设、尚未解决的歧义。对于不影响主流程的信息可以先采用有说明的假设；影响目标或可行性的歧义写入 `unresolved` 并向用户提出具体问题。
- 按 [工作区字段](../mm-contest/references/workspace.md) 编写 `problem.json` 和 `statement.md`。每个小问有唯一 id、text、depends_on。内置任务映射还需要正确的 task。
- 将原题和所有使用的附件放入 `raw/`，其他输入路径加入 input_files，以便变更检测。
- 运行 `mm run <工作区> --until analyze`，对照原题检查生成的 analysis.json。不要用自动通过代替题意审阅。

## 边界

内置 allocation 只接受 allocation、sensitivity 任务；forecast 只接受 comparison、forecast。复杂多问、综合评价、机理模型等使用 custom 适配器，由各小问的真实实现给出 coverage。人工把 task 标签改成支持类型，不会自动证明题意适配。
