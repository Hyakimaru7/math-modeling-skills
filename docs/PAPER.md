# 论文内容、数值和引用绑定

paper/content.json 包含 abstract、keywords 和 sections。每个 section 含 heading、text、question_ids。对每个赛题小问应有对应章节。

```json
{"abstract":"目标值为 {{metric:objective|.2f}}。","keywords":["整数规划"],"sections":[{"heading":"结果分析","text":"使用混合整数规划求解{{cite:scipy_milp}}。目标值为 {{metric:objective|.2f}}。","question_ids":["Q1"]}]}
```

标记规则：

- `{{metric:objective|.2f}}`：solution.metrics.objective，保留两位小数。
- `{{value:selected_model}}`：solution.selected_model，标量文本。
- `{{param:horizon|.0f}}`：problem.horizon，输入参数值。
- `{{cite:source_id}}`：引用 problem.sources 中已记录的来源。

点号可索引嵌套对象。正文中的裸阿拉伯数字会阻止构建，用绑定标记表示数值或参数；公式在 model.equations 中用 LaTeX 表达。表格与图从同一次 solution 生成。

claims.json 保存每次绑定的结果 id、字段、原值、格式和呈现值。该机制证明文字读取了哪个计算字段，不证明该字段的科学正确性；数据来源、题意与方法论证仍需作者核验。

来源 verification 的 human_verified 只由真实完成核验的人员填写，并附 verifier、verified_at。AI 打开页面只能记录 opened_by_agent。来源是否支持正文中的论断仍需阅读判断。

AI 使用记录以 mm log-ai 追加真实事实；人工审阅信息未知时保持为空。按赛事年份从官方要求核对并整理披露，不能凭空写“未使用 AI”或“已完成人工审核”。

生成 PDF 后渲染每页，检查公式、图表、引用、分页、溢出和字体。默认中文模板属于训练模板；使用其他比赛语言或格式需要在实际要求下调整。

## 模板

模板位于 src/math_modeling/assets/templates/paper.tex.j2，使用 Jinja 自定义分隔符，避免与 LaTeX 大括号冲突。正文文本自动转义；model.equations 是作者提供的 LaTeX 数学表达。

XeLaTeX 使用 -no-shell-escape，失败时保留 paper/build.log。ReportLab 是无需 TeX 的便携预览，公式以原始表达显示；正式数学排版使用 XeLaTeX。两种方式都会保留 manuscript.md、paper.tex 和 claims.json。

当前中文模板选择 Fandol 字体，包含训练草稿标记、公式、可分页表格、图表和来源列表。contest.max_pages 会检查生成页数；profile/year/language 是赛事上下文，并不会自动下载官方模板、检查匿名内容或切换英文格式。这些工作由 mm-paper / mm-review 按当前要求执行。

## 定量绑定范围

正文中的数值必须使用绑定标记，生成的结果表直接读取 solution.tables。模型公式和符号定义来自 model.json。数值绑定检查避免文本与结果字段不一致；它不会自动证明所有自然语言论断、数学推导或引用支持关系。

来源默认仍需作者人工核验。problem.sources 中 human_verified 仅应由实际核验人填写，并附 verifier、verified_at；构建不会把 AI 阅读记录升级为人工验证。
