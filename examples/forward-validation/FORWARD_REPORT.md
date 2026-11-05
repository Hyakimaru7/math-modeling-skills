# 独立前向验证记录

已使用 mm-contest 及其数据、建模、论文、审阅协议完成全新训练题，未编辑交付项目源码。

## 实际结果

- 原始机时 19、材料 21；产品 A 最低产量为 1，所有产量为整数且遵守各自上限。
- 最优生产数量 (A,B,C) = (6,7,0)，利润 122；资源用量分别为 19 和 20。
- 可行贪心基线利润 103，相对改善 18.4466%。LP 上界 123.6667。
- 全资源容量同步乘以 0.9/1.0/1.1，最优利润分别为 107/122/130。
- 工作区独立枚举脚本 independent_verify.py 对全部有限整数域枚举，三情景最优值均与求解器一致。
- 当前版本的 run 全流程完成，audit passed=true，status 全阶段 current；重复 run 七阶段均命中缓存。

## 产物

problem.json、statement.md、原始 CSV、model.json、solution.json、validation.json、checks.csv、tables、figures、code_snapshot、provenance、paper/manuscript.md、paper/paper.tex、paper/paper.pdf、claims.json、review、AI 使用记录和独立枚举程序/结果均已形成。

XeLaTeX PDF 共 4 页。已使用 PyMuPDF 渲染并检查全部页面，公式、表格、图表、中文和分页均清晰，无可见裁切或重叠。PDF 保持训练草稿，引用为 opened_by_agent，未冒充人工核验。

## 发现及处理

首次正文未使用 cite 标记时，模板的空 description 环境导致 XeLaTeX 报错。已向主代理报告，主代理已在模板加条件分支。主代理稳定源码后，本工作区已再次 run/audit 并通过。

当前宿主的 pdftoppm 报缺少 Adobe-GB1 语言映射并漏绘中文，属于渲染器配置；同一实际 XeLaTeX PDF 的嵌入字体与 PyMuPDF 渲染显示正常。建议主代理使用其可用的完整 Poppler 配置或 PyMuPDF 完成视觉 QA。

## 过程范围

这是一个新题的独立完整执行验证，不代表自动触发召回率或所有数学建模题型正确率。源码或依赖版本进一步变化时，应重新执行以刷新输入签名。
