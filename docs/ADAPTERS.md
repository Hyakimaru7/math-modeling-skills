# 自定义适配器

工作区 adapter.py 是宿主/队员编写并执行的 Python；运行前应阅读其逻辑。模块导入时避免求解、外部写入和网络请求。

四个必要函数：

```python
prepare(problem: dict, rows: list[dict]) -> dict
model(problem: dict, data: dict) -> dict
solve(problem: dict, data: dict, output_dir: Path) -> dict
validate(problem: dict, data: dict, result: dict) -> dict
```

prepare 返回 JSON 可序列化处理数据。model 至少有 family、variables、equations、assumptions、limitations；变量有 symbol、meaning、unit。可提供 selection、baseline。

solve 返回：

```json
{"status":"computed","metrics":{"score":1.0},"tables":{"scores":[{"method":"baseline","score":1.0}]},"coverage":{"Q1":"computed"}}
```

允许 status 为 optimal、computed、limit_reached、infeasible、unbounded、solver_error。无解时 metrics 可以含 null，后续核验应明确失败；optimal 需要相应数学或求解依据。coverage 必须与真实已实现的小问对应。

可选 figures 是列表，各项提供工作区内相对 path、caption、data；输出目录由适配器创建。生成图和原始表格均留在工作区。图片路径不能逃逸工作区。

validate 必须返回 checks 列表，至少一项；每项包含非空 name、布尔 passed、解释性 detail。运行器重新汇总 passed。针对当前数学问题设计独立核验，不能只检查文件存在或返回状态。

使用标准 JSON 可表示的有限数值；不输出 NaN/Infinity 或 NumPy 标量。随机种子从 problem.options.seed 读取。time_limit 由适配器显式传入求解器；运行器不会强行杀死任意 Python 模型。

可运行示例：`mm init runs/custom --case custom`，随后 `mm run runs/custom`。它用均值求解二次损失，并通过梯度和邻域扰动核验。

## 开发和验收

先选一个有可信结果的小问题实现四个函数，然后在未参与实现的新输入上验证。新增模型应有数学性质检查或独立算法交叉检查；不能用“结果等于自己上一次输出”作为唯一测试。

模型可以使用多个附件：prepare 中依据 problem.input_files 读取，原始文件应放在 raw/；所有原件进入输入哈希。运行时 prepare 的 rows 参数来自 data_file 所指定的主 CSV。

多小问适配器可以让 prepare 返回多个数据块，让 solve 按依赖顺序计算，并将中间结果保存在 JSON 可序列化字段中。最终每个已实现小问在 coverage 中有 computed。图表底层数据写入 tables；复杂模型新增依赖时写入 pyproject.toml 并更新验证快照。

custom 模块是普通本地 Python，会在模型运行进程中执行；它不是隔离沙箱。宿主工作区权限继续适用，模型计算以外的外部操作不由本包授权。
