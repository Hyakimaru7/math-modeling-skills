# 交付验证记录

验证日期：2026-11-05；版本：0.1.0。

## 执行结果

- 38 项自动测试全部通过，0 跳过。详见 evals/latest.json。
- 八个 skills 均通过官方 quick_validate.py 与项目引用链接检查。
- 最终 wheel 通过离线安装到独立 target 目录的导入及完整 custom 链路测试；测试使用已具备依赖的验证运行环境，没有声称重新下载验证所有平台依赖。
- 四个完整工作区的 run、audit 与 status 均通过。
- 15 页 XeLaTeX 中文 PDF 已逐页渲染并视觉检查，未发现裁切、重叠、缺字或表格标题孤立；编译日志未出现 Overfull、Missing character 或 LaTeX Warning。
- 当前宿主 Poppler 缺 Adobe-GB1 映射，采用 PyMuPDF 完成可靠渲染检查。

| 案例 | 关键结果 | PDF 页数 |
|---|---|---|
| allocation | 最优利润 605 | 4 |
| forecast | 测试 RMSE 2.108277 | 5 |
| custom | 中心值 5，损失 20 | 2 |
| forward-validation | 最优利润 122 | 4 |

## 独立前向验证

独立会话使用新题原件，实际完成建模、求解、枚举交叉核验、论文与 PDF。主方案 (6,7,0)，利润 122；容量情景的利润 107/122/130 均经另行枚举验证。重新执行七阶段全部命中缓存。原始输入、独立验证程序和报告保存在 examples/forward-validation/。

发现并修复了空来源时 LaTeX description 环境报错的问题，已经添加真实 XeLaTeX 回归测试；同时调整了表格标题跨页和负零显示。

## 评测范围

以上为数值、工作流、产物协议和一个新题的前向验证。evals/skill-prompts.jsonl 的 16 个宿主行为任务是可执行评测目录，尚未统计整体 LLM 路由准确率，不代表所有题型正确率或比赛获奖概率。

内置模型覆盖整数生产配置与日频基础预测；其他题型通过 custom 适配器由宿主/队员实现。论文模板为中文训练版，来源仍保留真实的人工核验状态。

## 已验证运行依赖

```json
{
  "python": "3.12.14",
  "math-modeling-skills": "0.1.0",
  "numpy": "2.3.5",
  "scipy": "1.18.1",
  "matplotlib": "3.11.2",
  "Jinja2": "3.1.6",
  "reportlab": "4.4.9",
  "pypdf": "6.18.0"
}
```

完整依赖闭包见 requirements-lock.txt。项目不需要 API key 执行已结构化案例。科学写作和可视化技能参考的文献已列入 ACKNOWLEDGEMENTS.md。
