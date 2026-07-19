from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class StrategyGenerationConfig:
    """策略生成默认约束。"""

    universe: str = "hs300"
    rebalance: str = "weekly"
    long_quantile: float = 0.2
    short_quantile: float = 0.0
    max_name_weight: float = 0.05
    max_industry_weight: float = 0.25
    max_turnover: float = 0.35
    cost_bps: float = 10.0
    min_utility: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
