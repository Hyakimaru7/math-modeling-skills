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