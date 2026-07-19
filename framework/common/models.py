from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class FactorMeta:
    """因子元信息。"""

    factor_id: str
    name: str
    category: str
    direction: int = 1  # 1: 越大越好; -1: 越小越好
    neutralize: tuple[str, ...] = ("industry", "size")
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["neutralize"] = list(self.neutralize)
        return data


@dataclass
class FactorEvalResult:
    """单因子评估结果。"""

    factor_id: str
    rank_ic_mean: float
    icir: float
    coverage: float
    turnover: float
    max_abs_corr_with_selected: float = 0.0
    passed: bool = False
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StrategySpec:
    """可执行策略规格。"""

    strategy_id: str
    version: str
    universe: str
    factors: list[str]
    factor_weights: dict[str, float]
    rebalance: str = "weekly"
    long_quantile: float = 0.2
    short_quantile: float = 0.0
    max_name_weight: float = 0.05
    max_industry_weight: float = 0.25
    max_turnover: float = 0.35
    cost_bps: float = 10.0
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TargetPosition:
    """目标持仓。"""

    symbol: str
    weight: float
    score: float
    industry: str = ""


class RiskLevel(str, Enum):
    L1_ALERT = "L1_ALERT"
    L2_DELEVERAGE = "L2_DELEVERAGE"
    L3_FREEZE = "L3_FREEZE"
    L4_OFFLINE = "L4_OFFLINE"


class RiskAction(str, Enum):
    ALERT = "ALERT"
    REDUCE_EXPOSURE = "REDUCE_EXPOSURE"
    FREEZE_OPEN = "FREEZE_OPEN"
    LIQUIDATE_OR_SWITCH = "LIQUIDATE_OR_SWITCH"


@dataclass
class NavSnapshot:
    """净值快照。"""

    date: str
    nav: float
    daily_return: float
    drawdown: float
    rolling_vol: float
    rolling_sharpe: float


@dataclass
class RiskEvent:
    """风控事件。"""

    date: str
    level: RiskLevel
    action: RiskAction
    reason: str
    metrics: dict[str, float] = field(default_factory=dict)
    scale: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "level": self.level.value,
            "action": self.action.value,
            "reason": self.reason,
            "metrics": self.metrics,
            "scale": self.scale,
        }
