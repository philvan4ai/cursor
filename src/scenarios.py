"""政策情景：管制路径 σ(t) 与关键事件冲击。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .model import EvolutionaryChipGame, GameParams, Trajectory


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    description: str
    params: GameParams
    sigma_path: Callable[[float], float]
    x0: float = 0.10
    y0: float = 0.25


def _piecewise_sigma(breakpoints: list[tuple[float, float]]) -> Callable[[float], float]:
    def path(t: float) -> float:
        s = breakpoints[0][1]
        for tb, sb in breakpoints:
            if t >= tb:
                s = sb
            else:
                break
        return s

    return path


# t=0 → 2021；t=4 → 2025；t=9 → 2030
SCENARIOS: dict[str, Scenario] = {
    "sell_soft": Scenario(
        name="sell_soft",
        label="卖：持续特供（H20 逻辑）",
        description=(
            "美方允许阉割版芯片对华销售，英伟达维持可观份额；"
            "中国大模型厂商算力瓶颈缓解，但国产替代激励偏弱。"
        ),
        params=GameParams(
            subsidy=0.07,
            wall_corner_boost=0.28,
            forced_migration=0.42,
            cuda_lockin=0.28,
            domestic_base=0.50,
            congestion_scale=1.25,
            adopter_speed=1.05,
        ),
        sigma_path=_piecewise_sigma(
            [(0.0, 0.35), (1.0, 0.50), (2.0, 0.55), (4.0, 0.52), (6.0, 0.50)]
        ),
        y0=0.24,
    ),
    "hard_ban": Scenario(
        name="hard_ban",
        label="不卖：高强度围堵",
        description=(
            "高端与特供一并收紧；供应风险与「墙角激励」同步上升，"
            "加速华为等国产栈的研发投入与客户迁移。"
        ),
        params=GameParams(
            subsidy=0.10,
            wall_corner_boost=0.52,
            forced_migration=0.62,
            switch_cost=0.12,
            cuda_lockin=0.22,
            congestion_scale=1.15,
            adopter_speed=1.20,
        ),
        sigma_path=_piecewise_sigma(
            [(0.0, 0.32), (1.0, 0.68), (2.0, 0.85), (3.5, 0.95), (5.0, 0.97)]
        ),
    ),
    "wsj_dilemma": Scenario(
        name="wsj_dilemma",
        label="WSJ 两难路径（基准校准）",
        description=(
            "先收紧高端，再释放「第4好」信号又反复；"
            "信任受损 + 昇腾性能跃迁，推动采用率贴近 10%→41%→75% 轨迹。"
        ),
        params=GameParams(
            subsidy=0.08,
            wall_corner_boost=0.42,
            forced_migration=0.58,
            switch_cost=0.16,
            cuda_lockin=0.26,
            domestic_base=0.52,
            domestic_rd_gain=0.38,
            congestion_scale=1.40,
            frontier_residual=0.55,
            kappa0=0.70,
            kappa_growth=0.020,
            adopter_speed=1.25,
            supplier_speed=1.00,
        ),
        sigma_path=_piecewise_sigma(
            [
                (0.0, 0.30),
                (1.0, 0.60),
                (2.0, 0.74),
                (3.0, 0.82),
                (4.0, 0.91),
                (5.0, 0.93),
                (7.0, 0.88),
            ]
        ),
        y0=0.24,
    ),
    "ascend_shock": Scenario(
        name="ascend_shock",
        label="性能冲击：昇腾 950 / 平头哥跃迁",
        description=(
            "在 WSJ 两难管制路径上，额外提高国产性能与降低迁移摩擦，"
            "刻画「打破无法取代英伟达」认知转折。"
        ),
        params=GameParams(
            subsidy=0.09,
            wall_corner_boost=0.45,
            forced_migration=0.52,
            switch_cost=0.10,
            cuda_lockin=0.18,
            domestic_base=0.56,
            domestic_rd_gain=0.40,
            congestion_scale=1.15,
            adopter_speed=1.25,
        ),
        sigma_path=_piecewise_sigma(
            [
                (0.0, 0.30),
                (1.0, 0.60),
                (2.0, 0.74),
                (3.0, 0.82),
                (4.0, 0.91),
                (5.0, 0.93),
            ]
        ),
        y0=0.32,
    ),
    "euv_breakthrough": Scenario(
        name="euv_breakthrough",
        label="反事实：EUV 突破（秦始皇摸电门）",
        description=(
            "假设先进光刻瓶颈解除，产能/良率天花板大幅抬升；"
            "演化稳定策略突破 DUV 约束，趋向更高国产化。"
        ),
        params=GameParams(
            euv_breakthrough=True,
            subsidy=0.08,
            wall_corner_boost=0.42,
            forced_migration=0.50,
            switch_cost=0.10,
            domestic_base=0.55,
            domestic_rd_gain=0.40,
            congestion_scale=0.45,
            frontier_residual=0.12,
            kappa_euv=0.97,
            adopter_speed=1.20,
        ),
        sigma_path=_piecewise_sigma(
            [(0.0, 0.30), (1.0, 0.60), (2.0, 0.74), (4.0, 0.91), (5.0, 0.93)]
        ),
        y0=0.28,
    ),
    "no_control": Scenario(
        name="no_control",
        label="反事实：无出口管制",
        description="σ 维持低位，CUDA 网络效应主导，国产替代缓慢爬升。",
        params=GameParams(
            subsidy=0.04,
            wall_corner_boost=0.08,
            forced_migration=0.12,
            switch_cost=0.24,
            cuda_lockin=0.36,
            domestic_base=0.48,
            congestion_scale=1.35,
            adopter_speed=0.80,
        ),
        sigma_path=lambda _t: 0.18,
        y0=0.20,
    ),
}


def run_scenario(scenario: Scenario, t_end: float = 9.0) -> Trajectory:
    game = EvolutionaryChipGame(scenario.params)
    return game.simulate(
        x0=scenario.x0,
        y0=scenario.y0,
        t_span=(0.0, t_end),
        n_steps=901,
        sigma_path=scenario.sigma_path,
        label=scenario.label,
    )


def run_all_scenarios(names: list[str] | None = None) -> dict[str, Trajectory]:
    keys = names or list(SCENARIOS.keys())
    return {k: run_scenario(SCENARIOS[k]) for k in keys}


def calibration_targets() -> dict[str, float]:
    return {
        "2021_domestic_share": 0.10,
        "2025_domestic_share": 0.41,
        "2030_domestic_share": 0.75,
        "2025_nvidia_share_idc": 0.55,
    }
