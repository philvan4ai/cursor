围绕三条主线构建可落地的智能量化策略体系：

1. **因子筛选 + 智能合成**：质量闸门、IC/ICIR、多重检验、冗余压缩，再做可解释加权合成
2. **策略生成**：信号合成、约束组合、效用评估、规格冻结
3. **净值风控**：回撤/波动分级、处置动作、审计闭环

详细设计见：
- [`docs/智能量化策略设计框架.md`](docs/智能量化策略设计框架.md)
- [`docs/因子筛选与智能合成.md`](docs/因子筛选与智能合成.md)（因子层专题）

## 目录结构

```
docs/                         # 设计框架文档
framework/
  common/                     # 数据模型
  factor_screening/           # 因子筛选 + 智能合成
  strategy_generation/        # 策略生成
  nav_risk/                   # 净值风控
examples/end_to_end_demo.py   # 端到端演示
tests/test_framework.py       # 单元测试
```

## 快速开始

```bash
# 运行测试
python3 -m unittest tests/test_framework.py

# 运行端到端演示
python3 examples/end_to_end_demo.py
```

## 最小调用示例

```python
from framework import FactorScreeningPipeline
from framework.common.models import FactorMeta

# 筛选 + 智能合成
result = FactorScreeningPipeline().run_with_synthesis(
    factor_metas=[
        FactorMeta("mom", "动量", "price"),
        FactorMeta("ep", "价值", "fundamental"),
    ],
    rank_ic_map={
        "mom": [0.03, 0.04, 0.035, 0.045],
        "ep": [0.025, 0.03, 0.028, 0.032],
    },
    coverage_map={"mom": 0.95, "ep": 0.9},
    turnover_map={"mom": 0.3, "ep": 0.15},
    corr_matrix={("mom", "ep"): 0.2},
)
print(result["selected_ids"])
print(result["synthesis"]["weights"])
```

## 设计要点

- **研究生产同构**：策略以 `strategy_spec` 版本化输出
- **防过拟合**：筛选含 FDR / 相关性压缩，合成含相关惩罚与再验收
- **风险前置**：风控分级（L1–L4）可直接缩放敞口并回写审计事件