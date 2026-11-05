---
name: mm-code
description: "将已确定的数学模型实现为可运行求解、实验和绘图代码。用于比赛模型编程、适配器扩展、求解错误修复与结果保存。"
---

将公式落实到可重复执行的代码，保留原始数据、参数、随机种子、软件版本和求解状态。

## 实现约定

读 [自定义适配器协议](references/adapter.md)。适合参考题型时使用内置求解器；真实问题超出接口时，在工作区编写 adapter.py 的 prepare、model、solve、validate 函数。例子 `mm init <工作区> --case custom` 可以完整运行，也可替换为当前题目的实现。

- 核对最大化与最小化、矩阵行列含义、整数域、上下界和目标单位。
- 返回机器可读的 status、metrics、tables、coverage。只把确实完成的小问标为 computed。
- 优化区分最优、可行但达到限制、不可行、无界和错误；启发式结果不无条件称为全局最优。
- 预测先冻结验证方案，记录训练与测试范围；最终测试不用于反复选模。
- 随机算法使用 problem.options.seed。求解器和实验按用户预算设置时间、迭代和候选数量上限；CLI 不会为任意 custom Python 强制中断，由适配器实现算法预算。
- 图片保存到工作区 figures，提供明确标题、单位、图注和底层数据路径。图中误差范围应说明含义；未计算的不确定性不绘制。

执行 `mm run <工作区> --until solve`，检查 solution.json、tables 与 provenance.json。出现报错时先用最小可复现输入定位，然后重跑受影响阶段。
