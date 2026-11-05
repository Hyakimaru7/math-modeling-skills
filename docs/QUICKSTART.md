# 从真实赛题开始

## 首次使用

1. 解压完整工程，安装依赖，在 Codex 中打开工程目录。
2. 给出赛题及附件位置，使用 `$mm-contest` 明确语言、赛事年份与时间预算。
3. 宿主 AI 读取原题，将所用原件复制进独立工作区 raw/；记录题号、附件和单位来源。
4. 由宿主/队员建立 problem.json。内置接口确实适配才选择 allocation/forecast，否则从 custom 工作区开始，替换题目、数据、适配器及正文。
5. `mm run <工作区> --until model` 后审阅题意、假设与公式；无需为每一次常规计算单独确认。影响目标或可行性的歧义应先说明。
6. 运行到 validate，修正错误并记录实际实验，再撰写与结果绑定的正文。
7. 追加真实 AI 使用信息，构建论文，运行 audit，并渲染全部 PDF 检查。

## 接口示例

```bash
mm init runs/my-contest --case custom
```

这会复制一个能运行的二次损失教学题。宿主需要按照当前赛题替换 `problem.json`、`statement.md`、`raw/`、`adapter.py`、`paper/content.json`；没有完成替换时，它仍然只是教学示例。

原始 PDF、Excel、多表数据由宿主和适配器处理。CLI 内置读入 CSV，不内置通用 PDF OCR 或 Excel 语义解释。原始附件保留，转换代码应可复现；转换后的 CSV 可以作为 data_file。

## 修改与恢复

- 改数据或约束：编辑输入文件或 problem.json，执行 mm run。
- 改公式和算法：编辑 adapter.py，执行 mm run。
- 改论证和摘要：编辑 paper/content.json，执行 mm run；已验证计算可以复用。
- 中断后恢复：查看 mm status，再执行 mm run。
- 产物损坏：mm audit 显示问题，mm run 从受影响阶段重建。
- 保留两个方案比较：创建两个独立工作区，各自保存输入和结果。

直接修改生成的 solution.json、paper.tex 或 manuscript.md 会触发完整性提示。将长期改动写回适配器、正文模板或项目模板。

## 训练模式和预算

快速、标准、深入是 skill 的工作优先级，由宿主控制候选方法和实验次数。options.time_limit 是内置 MILP 每次调用的上限，不是整个比赛的倒计时。自定义优化与仿真需要在代码中设置各自预算。
