from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class FactorScreeningConfig:
    """因子筛选阈值配置。"""

    min_abs_rank_ic: float = 0.02
    min_icir: float = 0.3
    min_coverage: float = 0.8
    max_turnover: float = 0.6
    max_corr: float = 0.7
    fdr_alpha: float = 0.1
    prefer_higher_icir: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
