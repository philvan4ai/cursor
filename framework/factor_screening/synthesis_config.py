from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SynthesisConfig:
    """因子智能合成配置。"""

    # 相关惩罚强度：越大越倾向分散到低相关因子
    corr_penalty: float = 0.5
    # 单因子权重上下限
    min_weight: float = 0.05
    max_weight: float = 0.50
    # 权重平滑：新权重 = (1-s)*old + s*raw；无旧权重时忽略
    smooth: float = 0.4
    # 合成因子再验收阈值
    min_syn_abs_ic: float = 0.02
    min_syn_icir: float = 0.35

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
