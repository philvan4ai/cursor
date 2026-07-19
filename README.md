# 智能量化策略设计框架

围绕三条主线构建可落地的智能量化策略体系：

1. **因子筛选**：质量闸门、IC/ICIR、多重检验、冗余压缩
2. **策略生成**：信号合成、约束组合、效用评估、规格冻结
3. **净值风控**：回撤/波动分级、处置动作、审计闭环

详细设计见 [`docs/智能量化策略设计框架.md`](docs/智能量化策略设计框架.md)。

## 目录结构

```
docs/                         # 设计框架文档
framework/
  common/                     # 数据模型
  factor_screening/           # 因子筛选
  strategy_generation/        # 策略生成
  nav_risk/                   # 净值风控
examples/end_to_end_demo.py   # 端到端演示
tests/test_framework.py       # 单元测试
```

## 快速开始

```bash
# 运行测试
python -m unittest tests/test_framework.py

# 运行端到端演示
python examples/end_to_end_demo.py
```

## 最小调用示例

```python
from framework import (
    FactorScreeningPipeline,
    StrategyGenerationEngine,
    NavRiskManager,
)
from framework.common.models import FactorMeta

# 1) 因子筛选
result = FactorScreeningPipeline().run(
    factor_metas=[FactorMeta("mom", "动量", "price")],
    rank_ic_map={"mom": [0.03, 0.04, 0.035]},
    coverage_map={"mom": 0.95},
    turnover_map={"mom": 0.3},
)

# 2) 策略生成
engine = StrategyGenerationEngine()
strategy = engine.run(
    strategy_id="alpha",
    version="0.1.0",
    factor_icir={"mom": 0.8},
    factor_values={"mom": {"A": 1.0, "B": 0.2}},
    industries={"A": "tech", "B": "fin"},
    expected_excess=0.08,
    expected_vol=0.12,
    expected_turnover=0.2,
)

# 3) 净值风控
risk = NavRiskManager().run(
    dates=["2024-01-01", "2024-01-02", "2024-01-03"],
    navs=[1.0, 0.97, 0.90],
    current_exposure=1.0,
)
```

## 设计要点

- **研究生产同构**：策略以 `strategy_spec` 版本化输出
- **防过拟合**：筛选含 FDR / 相关性压缩，生成侧效用含成本与换手
- **风险前置**：风控分级（L1–L4）可直接缩放敞口并回写审计事件
