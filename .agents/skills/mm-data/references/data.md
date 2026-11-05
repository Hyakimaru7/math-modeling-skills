# 参考数据接口

## allocation

CSV 列为 product,profit,min_units,max_units，及 problem.resources 中每个资源名。产品名唯一，所有数字有限，产量上下界为非负整数且下界不超过上界。资源消耗与资源容量非负；每个资源须给单位。profit 可以为负，此时程序尊重最低产量约束。

resources 示例：{"labor":25,"material":23}；units 示例：{"quantity":"件","profit":"利润单位/件","labor":"工时","material":"材料单位"}。

内置模型只支持最大化线性利润与资源上限。需求下限、开工费、非线性关系、跨期库存等请编写 custom 适配器，不能通过换列名假装支持。

## forecast

CSV 列为 date,value，date 是严格连续、升序、无重复的 ISO 日期，value 是有限数值；至少 42 个日观测。holdout 在 7 到样本数三分之一之间，horizon 在 1 到 90 之间。输入缺失、异常日期或非有限值时停止，由处理代码显式解决。

候选为周朴素、线性趋势、趋势加固定周周期。候选比较在最终测试期之前进行；最后一次测试后，用全部已观测数据拟合未来预测。该参考实现不包含外生变量或自动校准预测区间。

## custom

CSV 先由标准读入器检查表头，再传给 prepare(problem,rows)。其他附件从 problem.input_files 和 raw/ 读取；路径应限定在工作区。prepare 返回可 JSON 序列化的数据，以及 rows 和 quality 记录。