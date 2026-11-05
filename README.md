# MathModeling Skills

MathModeling Skills 是一套用于数学建模比赛的 Codex 技能和 Python 工具。它把赛题分析、数据准备、模型建立、代码求解、结果检验和论文编写放在同一个工作目录中，便于逐步推进、复现计算和修改论文。

在 Codex 中，skills 指导赛题理解、方法选择、代码编写和正文撰写；Python 命令负责执行计算、保存结果、检查数值和构建 PDF。每次运行都保留输入、代码版本、求解状态及产物记录。

当前支持整数生产配置和日频预测，也提供自定义模型接口。其他赛题可以按相同接口编写模型，再使用已有的核验、图表和论文工具。

## 目录

- [功能范围](#功能范围)
- [安装](#安装)
- [在 Codex 中使用](#在-codex-中使用)
- [八个 skills 的分工](#八个-skills-的分工)
- [处理自己的赛题](#处理自己的赛题)
- [论文、图表与数值绑定](#论文图表与数值绑定)
- [检查进度、恢复任务和更新结果](#检查进度恢复任务和更新结果)
- [编写自定义模型](#编写自定义模型)
- [命令说明](#命令说明)
- [测试](#测试)
- [项目结构](#项目结构)
- [常见问题](#常见问题)
- [参考资料与许可证](#参考资料与许可证)

## 功能范围

| 环节 | 提供的功能 | 主要产物 |
| --- | --- | --- |
| 赛题分析 | 拆分小问，记录小问依赖，区分给定条件、假设和待确认事项 | `problem.json`、`analysis.json` |
| 数据准备 | 检查字段、重复、缺失、非有限值、单位和日期顺序；保留原始附件 | `data/processed.json`、`data/quality.json` |
| 模型建立 | 定义变量、公式、约束、基线和适用范围；比较候选方法 | `model.json` |
| 编程求解 | 执行内置或自定义模型，保存指标、结果表和求解状态 | `solution.json`、`tables/` |
| 结果检验 | 复算目标和误差，检查约束、整数域、时间划分及数学性质 | `validation.json`、`checks.csv` |
| 图表 | 根据本次计算生成图表，保留底层数据和图片来源 | `figures/` |
| 论文 | 将正文中的数值与计算字段绑定，生成 Markdown、LaTeX 和 PDF | `paper/` |
| 审阅与复现 | 检查输入和产物是否过期，核对论文数值，记录未决问题 | `state.json`、`provenance.json`、`review.json` |

输入或代码变化后，运行器会重建受影响阶段及其下游。只修改正文时，可以复用已经完成的计算。生成文件被删除或改写后，完整性检查也会发现变化。

项目使用本地 Python 运行模型。执行已配置的模型不需要模型 API key；自然语言分析与撰稿使用当前 Codex 会话提供的能力。CLI 接收结构化输入，原始 PDF、Excel 和复杂附件由 Codex 与数据处理代码读取、解释和转换。

## 安装

### 环境要求

- Python 3.11 或更新版本。
- NumPy、SciPy、Matplotlib、Jinja2、ReportLab 和 pypdf，由项目依赖配置安装。
- 使用中文 LaTeX 排版时，需要 XeLaTeX、ctex 和 Fandol 字体，可通过 TeX Live、MacTeX 或 MiKTeX 安装。

项目依赖的版本范围见 `pyproject.toml`。

### 获取项目并安装依赖

macOS 或 Linux：

```bash
git clone https://github.com/Hyakimaru7/math-modeling-skills.git
cd math-modeling-skills

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .

mm doctor
```

Windows PowerShell：

```powershell
git clone https://github.com/Hyakimaru7/math-modeling-skills.git
cd math-modeling-skills

py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -e .

mm doctor
```

`mm doctor` 会列出 Python 依赖及 PDF 工具的可用情况。依赖已经安装时，也可以直接用 `python scripts/mm.py` 替代下文中的 `mm`。

### PDF 排版

默认先检查 `xelatex`。工具存在时使用 LaTeX 排版；不存在时生成 ReportLab 便携预览，同时保留 LaTeX 源文件。

```bash
# 使用 LaTeX 排版
mm run runs/my-contest --engine xelatex

# 使用无需 TeX 的便携预览
mm run runs/my-contest --engine reportlab
```

便携预览适合检查内容，公式以原始表达显示。包含正式数学公式的排版建议使用 XeLaTeX。当前模板是中文训练模板，参加比赛时应按赛事和年份核对、调整格式。

`requirements-lock.txt` 保存了验证环境的依赖版本。需要复现该环境时，可在适合的 Python 和平台下使用：

```bash
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
```

## 在 Codex 中使用

在 Codex 中打开本项目目录，使用 `$mm-contest` 调用完整流程。例如：

```text
请使用 $mm-contest 处理我提供的赛题和附件，工作区放在 runs/my-contest。

完成各小问的建模、代码、结果检验和中文论文草稿。
每个小问先完成一个可解释的基线，再根据结果决定是否改进。
保留原始附件，说明额外假设，最后给出 PDF、源码和复现步骤。
```

已有工作区也可以继续处理：

```text
请使用 $mm-contest 接着处理 runs/my-contest。
先检查当前进度，保留我修改的模型和正文，完成剩余计算与论文。
```

只需要某个环节时，可以直接调用对应 skill：

```text
请使用 $mm-model 检查这道题的变量定义和约束是否完整。

请使用 $mm-validate 独立复算 runs/my-contest 的目标值和资源约束。

请使用 $mm-paper 根据已通过检验的结果修改摘要和结果分析。
```

### 安装到另一个项目

```bash
python scripts/install_skills.py --target /path/to/project/.agents/skills
```

脚本会复制本包的八个 skills。目标目录已有同名 skill 时默认停止，需要替换时再加 `--replace`。目标项目使用的 Python 环境还需要安装本项目运行器。

Python wheel 只安装运行器和内置资源。使用 Codex skills 时，还需要保留完整仓库中的 `.agents/skills/`，或执行上述安装脚本。

## 八个 skills 的分工

| Skill | 用途 | 入口文件 |
| --- | --- | --- |
| `mm-contest` | 安排完整解题流程，衔接模型、计算和论文，恢复中断任务 | [SKILL.md](.agents/skills/mm-contest/SKILL.md) |
| `mm-analyze` | 阅读赛题，整理小问目标、依赖、给定条件和假设 | [SKILL.md](.agents/skills/mm-analyze/SKILL.md) |
| `mm-data` | 检查附件，明确单位、日期、缺失和数据转换方法 | [SKILL.md](.agents/skills/mm-data/SKILL.md) |
| `mm-model` | 选择方法，建立变量、公式、约束和比较基线 | [SKILL.md](.agents/skills/mm-model/SKILL.md) |
| `mm-code` | 实现求解、实验、绘图及自定义适配器 | [SKILL.md](.agents/skills/mm-code/SKILL.md) |
| `mm-validate` | 检查计算结果，设计交叉核验和敏感性实验 | [SKILL.md](.agents/skills/mm-validate/SKILL.md) |
| `mm-paper` | 撰写与结果绑定的正文，构建并检查论文 PDF | [SKILL.md](.agents/skills/mm-paper/SKILL.md) |
| `mm-review` | 对照原题审阅模型、代码、图表和论文的一致性 | [SKILL.md](.agents/skills/mm-review/SKILL.md) |

每个 skill 都有明确的使用范围和步骤，详细接口或方法说明放在相应的 `references/` 中。完整流程共享同一工作区，避免小问之间重复使用不同版本的数据或参数。

## 处理自己的赛题

### 1. 保存原件并整理问题

将使用的赛题和附件放入工作区的 `raw/`。在 `statement.md` 中记录题意解释，在 `problem.json` 中记录目标、小问、单位、假设及数据来源。

每个小问有唯一编号和依赖关系。例如：

```json
{
  "questions": [
    {
      "id": "Q1",
      "text": "估计后续优化所需的需求参数。",
      "depends_on": []
    },
    {
      "id": "Q2",
      "text": "根据需求参数确定资源配置方案。",
      "depends_on": ["Q1"]
    }
  ]
}
```

这段内容展示小问结构，完整配置还需要 `schema_version`、`kind`、`title`、`data_file`、`data_origin`、`units` 和 `assumptions` 等字段。可从初始化配置修改，也可参考 [`schemas/problem.schema.json`](schemas/problem.schema.json)。影响计算的歧义写入 `unresolved`；这些事项没有明确前，分析阶段会停止并给出提示。

### 2. 选择计算接口

| `kind` | 已实现的任务 | 输入要求 |
| --- | --- | --- |
| `allocation` | 最大化线性利润，整数产量，上下界和资源容量约束；同步容量情景 | 产品 CSV、资源容量与单位 |
| `forecast` | 比较周朴素、线性趋势、趋势加周周期模型；训练内验证、留出评价和未来预测 | 连续日频的 `date,value` CSV |
| `custom` | 当前赛题自行实现的模型，包括多小问衔接 | 主 CSV、所需附件与 `adapter.py` |

内置 `allocation` 的小问任务字段只接受 `allocation`、`sensitivity`；`forecast` 只接受 `comparison`、`forecast`。需求约束、跨期库存、路径规划、综合评价、微分方程或仿真等超出参考模型接口的题目，应使用 `custom` 实现相应逻辑。

从自定义接口开始：

```bash
mm init runs/my-contest --case custom
```

该命令使用内置模板建立工作区。处理自己的赛题时，请按题目更新配置、原始数据、模型代码和正文内容。完整步骤见 [真实赛题上手说明](docs/QUICKSTART.md)。

### 3. 分阶段运行并检查

```bash
# 检查题意解释、数据和模型记录
mm run runs/my-contest --until model

# 执行求解与数值检验
mm run runs/my-contest --until validate

# 完成论文与审阅
mm run runs/my-contest
```

模型选择和数学判断由 Codex 与队员完成。运行器检查已写入配置和代码的条件，题意是否解释充分仍需要对照原题审阅。

## 论文、图表与数值绑定

### 正文如何引用结果

论文内容写在 `paper/content.json` 中。需要展示计算结果时，使用字段标记，构建时再从本次运行结果取值。正文中的计算字段可以按以下格式引用：

```json
{
  "abstract": "本次模型的目标值为 {{metric:objective|.2f}}。",
  "keywords": ["数学建模"],
  "sections": [
    {
      "heading": "结果分析",
      "text": "计算得到的目标值为 {{metric:objective|.2f}}。",
      "question_ids": ["Q1"]
    }
  ]
}
```

`question_ids` 应与题目中的小问编号一致，引用的字段应由当前模型实际计算产生。引用外部资料时，使用 `{{cite:source_id}}`，并在 `problem.sources` 中保存相应来源。

| 标记 | 读取位置 | 用途 |
| --- | --- | --- |
| `{{metric:objective\|.2f}}` | `solution.metrics.objective` | 将结果保留两位小数 |
| `{{value:selected_model_name}}` | `solution.selected_model_name` | 引用模型名称等标量文本 |
| `{{param:horizon\|.0f}}` | `problem.horizon` | 引用输入参数 |
| `{{cite:source_id}}` | `problem.sources` | 引用已记录的文献或官方资料 |

正文中的阿拉伯数字需要通过绑定标记引用；模型公式写在 `model.equations` 中。论文表格直接读取同一次实验的结果表，图片从对应的图表清单读取。

构建后，`paper/claims.json` 保存字段路径、原值、格式、呈现值和结果编号。这样可以检查摘要、正文和结果记录中的数值是否一致。数值绑定说明文本读取了哪个字段，模型假设和结论是否合理仍需判断。

### 文献与使用记录

来源记录保存在 `problem.sources` 中，包括标题、URL、访问日期和核验状态。AI 已打开来源时记录 `opened_by_agent`；真实完成的人工核验可以记录 `human_verified`，并填写核验人和日期。

实际 AI 使用情况可以追加到工作区：

```bash
mm log-ai runs/my-contest \
  --tool Codex \
  --model unknown \
  --purpose "辅助编写求解代码和修改论文" \
  --human-review "填写实际完成的人工修改和核验"
```

工具名称、模型版本、用途和人工核验内容应据实填写。记录追加后，再执行 `mm run` 更新论文审阅状态。比赛所需的声明和附件应按当年官方要求整理。

### 模板和图表

论文模板位于 [`paper.tex.j2`](src/math_modeling/assets/templates/paper.tex.j2)，可调整章节、页眉、字体、页边距和参考来源布局。`contest.max_pages` 用于检查生成页数；赛事名称、年份和语言字段用于记录上下文，具体模板及语言需要相应修改。

内置图表同时保存 PNG 和矢量 PDF，并保留底层数据路径。

论文输出为供队员审阅的草稿。提交前还需要检查原题覆盖、数学推导、来源支持及 PDF 排版。详细说明见 [论文绑定与排版](docs/PAPER.md)。

## 检查进度、恢复任务和更新结果

流程分为七个执行阶段：

```text
analyze → data → model → solve → validate → paper → review
```

每个阶段记录输入签名和产物哈希。重复运行时，输入与产物均未变化的阶段显示 `[cached]`；完成新计算后显示 `[done]`。

| 修改内容 | 处理方式 |
| --- | --- |
| 原始附件、问题配置、模型代码或依赖版本变化 | 保守重建计算及后续阶段 |
| 只修改 `paper/content.json` | 复用已有计算，重建论文和审阅 |
| 删除 PDF | 重建论文及后续审阅 |
| 改写结果文件或删除图文件 | 识别产物变化，从相关阶段重新运行 |
| 计算失败 | 保存失败阶段与错误信息，下游保持待重建状态 |

```bash
mm status runs/my-contest
mm audit runs/my-contest
mm run runs/my-contest
```

`status` 查看当前进度，`audit` 执行检查；这两个命令不会修复文件。`run` 根据依赖关系计算和重建。过去生成的文件可能仍在目录中，应以当前状态和审阅结果判断是否有效。

需要完整重算时：

```bash
mm run runs/my-contest --force
```

长期修改应写回 `problem.json`、原始数据处理程序、`adapter.py` 或 `paper/content.json`。直接编辑生成的 `solution.json`、`paper.tex` 和 `manuscript.md` 会触发完整性检查，也可能在下次构建时被覆盖。

同一个工作区同一时间由一个进程写入。比较不同方案时，使用不同工作区分别保存输入和结果。

## 编写自定义模型

`custom` 工作区中的 `adapter.py` 需要提供四个函数：

```python
def prepare(problem, rows):
    """读取、检查和转换输入，返回可保存为 JSON 的处理数据。"""


def model(problem, data):
    """返回模型类别、变量、公式、假设和局限。"""


def solve(problem, data, output_dir):
    """执行计算，返回状态、数值指标、结果表和小问完成情况。"""


def validate(problem, data, result):
    """独立检查结果，返回带布尔通过状态的检查列表。"""
```

上面的代码用于说明函数签名。四个函数的字段和返回值要求见 [自定义模型文档](docs/ADAPTERS.md)。

`solve` 的结果结构示例：

```json
{
  "status": "computed",
  "metrics": {"score": 1.0},
  "tables": {
    "comparison": [{"method": "baseline", "score": 1.0}]
  },
  "coverage": {"Q1": "computed"}
}
```

`validate` 至少返回一项检查：

```json
{
  "checks": [
    {
      "name": "objective_recomputed",
      "passed": true,
      "detail": "依据原始输入独立复算目标值。"
    }
  ]
}
```

运行器会根据各项 `passed` 重新汇总核验结果。检查应当对应数学性质，例如目标复算、约束、守恒、解析特例、时间边界或独立算法。仅检查文件存在或求解器返回成功，不能说明模型正确。

自定义模型可以读取多个附件、依次求解多个小问，也可以增加当前题目需要的依赖。随机种子和计算预算应在适配器中实际传入算法。`options.time_limit` 是内置优化每次求解的上限；自定义 Python 代码需要自行实现相应时间或迭代限制。

接口字段、图表约定和扩展步骤见 [自定义模型文档](docs/ADAPTERS.md)。

## 命令说明

| 命令 | 作用 |
| --- | --- |
| `mm doctor` | 检查依赖、版本和 PDF 工具 |
| `mm init PATH --case allocation` | 初始化整数配置工作区 |
| `mm init PATH --case forecast` | 初始化日频预测工作区 |
| `mm init PATH --case custom` | 初始化自定义模型工作区 |
| `mm run PATH` | 执行到论文和审阅阶段，复用仍有效的产物 |
| `mm run PATH --until STAGE` | 执行到指定阶段 |
| `mm run PATH --force` | 完整重算 |
| `mm run PATH --engine xelatex` | 使用 XeLaTeX 生成论文 |
| `mm run PATH --engine reportlab` | 使用便携预览排版 |
| `mm status PATH` | 查看进度和过期状态 |
| `mm audit PATH` | 检查当前输入、结果、正文和产物一致性 |
| `mm log-ai PATH ...` | 追加实际 AI 使用记录 |

`--until` 可选值为 `analyze`、`data`、`model`、`solve`、`validate`、`paper`、`review`。

命令退出状态：`run` 成功返回 `0`；`status` 全部阶段有效时返回 `0`，其他进度状态返回 `1`；`audit` 通过返回 `0`，检查失败返回 `2`。输入或构建错误返回非零状态，具体原因写在终端和相应产物中。

已配置的计算任务还可以通过工作区的复现脚本重建：

```bash
python runs/my-contest/reproduce.py
```

该脚本需要使用已安装本项目依赖的 Python 环境。

## 测试

运行结构检查和自动测试：

```bash
python scripts/check_skills.py
python scripts/evaluate.py
```

测试使用临时工作区，执行结果写入 `evals/latest.json`。XeLaTeX 未安装时，对应的可选测试会跳过，报告会记录跳过数量。

## 项目结构

```text
math-modeling-skills/
├── .agents/skills/           八个 skills 及其参考资料
├── src/math_modeling/        工作流、模型、图表和论文运行器
│   └── assets/
│       └── templates/       中文 LaTeX 模板
├── schemas/                 问题、结果和正文的 JSON Schema
├── scripts/                 源码运行、安装 skills、评测和打包工具
├── tests/                   数学结果与工作流测试
├── evals/                   测试记录与行为检查配置
├── docs/                    接口、架构、排版和来源说明
├── pyproject.toml           Python 包和命令入口配置
├── requirements-lock.txt    验证环境的依赖版本
└── LICENSE                  MIT 许可证
```

每个解题工作区的主要文件：

```text
workspace/
├── problem.json             问题、参数、单位、来源和小问依赖
├── statement.md             题意解释
├── raw/                     原始附件
├── adapter.py               自定义模型代码，custom 使用
├── analysis.json            结构化问题分析
├── data/                    处理后的数据及质量记录
├── model.json               变量、公式、假设与方法说明
├── solution.json            本次计算的状态和结果
├── tables/                  结果表格
├── figures/                 图表及其来源清单
├── code_snapshot/           本次运行使用的源码快照
├── validation.json          自动核验明细
├── checks.csv               便于逐项阅读的检查表
├── provenance.json          输入摘要、依赖版本与数据来源
├── state.json               阶段状态与产物哈希
├── paper/
│   ├── content.json         可编辑正文和绑定标记
│   ├── manuscript.md        生成的正文
│   ├── paper.tex            LaTeX 排版源文件
│   ├── paper.pdf            论文 PDF
│   ├── claims.json          结果引用记录
│   └── build.json           排版引擎、页数和草稿状态
├── review.json              审阅结果及待处理事项
├── reproduce.py             重建计算与论文的入口
└── ai_usage.jsonl            实际 AI 使用记录
```

## 常见问题

**为什么有些题要写适配器？**

不同赛题的变量、约束和数据关系不同。内置模型有明确接口，复杂题目由 Codex 和队员实现相应的 `adapter.py`，再使用同一套执行和论文工具。具体数学方法并不由一个固定分类器自动决定。

**为什么修改正文后还要运行命令？**

正文模板中的数值需要重新取值，PDF 和审阅记录也要更新。只改 `content.json` 时，前面的计算可以命中缓存。

**为什么计算完成了，却没有新的论文？**

先查看 `validation.json` 和失败阶段。核验不通过、正文引用了不可用数值、来源标记不存在或小问没有对应章节时，论文构建会停止。旧文件可能仍在，应以 `status` 和本次错误信息为准。

**XeLaTeX 编译失败怎么办？**

检查 `paper/build.log`，确认已安装 ctex 和 Fandol 字体，并检查公式及修改后的模板。只需预览内容时可以选择 `--engine reportlab`。已发现部分精简 Poppler 环境缺少中文 CMap；遇到渲染缺字时可用完整 Poppler 配置或 PyMuPDF 复核同一 PDF。

**`audit` 通过是否表示论文可以直接提交？**

它表示已编码的一致性检查通过。题意理解、推导、假设合理性、引用支持、匿名要求和当年赛事格式仍需队员检查。项目不执行自动投稿。

## 参考资料与许可证

- [真实赛题上手说明](docs/QUICKSTART.md)
- [自定义模型接口](docs/ADAPTERS.md)
- [论文绑定与排版](docs/PAPER.md)
- [架构与数据契约](docs/ARCHITECTURE.md)
- [评测范围](docs/EVALUATION.md)
- [官方来源](docs/SOURCES.md)
- [方法与技能致谢](ACKNOWLEDGEMENTS.md)

项目代码和技能说明采用 [MIT 许可证](LICENSE)。第三方依赖及引用资料保留各自许可证和权利声明。
