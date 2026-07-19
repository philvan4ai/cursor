from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class NavRiskConfig:
    """净值风控分级阈值。"""

    # 回撤阈值（正数，表示跌幅）
    soft_drawdown: float = 0.05
    hard_drawdown: float = 0.10
    freeze_drawdown: float = 0.15
    offline_drawdown: float = 0.20

    # 滚动波动阈值
    soft_vol: float = 0.20
    hard_vol: float = 0.30

    # L2 降仓比例（相对当前敞口）
    deleverage_scale: float = 0.5

    rolling_window: int = 20

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
