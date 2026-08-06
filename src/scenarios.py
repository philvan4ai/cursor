"""政策与气候情景：限制路径 × 气候目标。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .model import BatteryPolicyGame, GameParams, Trajectory


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    description: str
    params: GameParams
    r0: float = 0.28
    f0: float = 0.30
    instrument_path: Callable[[float], tuple[float, float, float]] | None = None


def _freeze_instruments(
    tau: float, mu: float, access: float
) -> Callable[[float], tuple[float, float, float]]:
    return lambda _t: (tau, mu, access)


def _piecewise_instruments(
    breakpoints: list[tuple[float, tuple[float, float, float]]]
) -> Callable[[float], tuple[float, float, float]]:
    def path(t: float) -> tuple[float, float, float]:
        val = breakpoints[0][1]
        for tb, vb in breakpoints:
            if t >= tb:
                val = vb
            else:
                break
        return val

    return path


# t=0 → 2023；t=2 → 2025；t=7 → 2030
SCENARIOS: dict[str, Scenario] = {
    "open_steps": Scenario(
        name="open_steps",
        label="开放合作 × STEPS",
        description=(
            "反事实：各国抑制关税与矿产壁垒，供应链保持一体化；"
            "气候目标按 IEA STEPS（现有政策）装机倍率增长。"
        ),
        params=GameParams(
            climate="STEPS",
            escalate=False,
            tau0=0.12,
            mu0=0.08,
            access0=0.10,
            industrial_rent=0.35,
            localization_subsidy=0.28,
            climate_penalty_scale=0.55,
            climate_internalization=0.40,
            policy_speed=0.85,
            industry_speed=0.90,
        ),
        r0=0.18,
        f0=0.20,
        instrument_path=_freeze_instruments(0.12, 0.08, 0.10),
    ),
    "open_nze": Scenario(
        name="open_nze",
        label="开放合作 × NZE",
        description=(
            "气候雄心最高（NZE）且政策保持开放：规模效应与气候惩罚共同压制限制策略，"
            "用作「理想路径」上界对照。"
        ),
        params=GameParams(
            climate="NZE",
            escalate=False,
            tau0=0.10,
            mu0=0.08,
            access0=0.10,
            industrial_rent=0.32,
            localization_subsidy=0.25,
            climate_penalty_scale=0.85,
            climate_internalization=0.55,
            open_scale_gain=0.50,
            policy_speed=0.90,
            industry_speed=0.95,
        ),
        r0=0.16,
        f0=0.18,
        instrument_path=_freeze_instruments(0.10, 0.08, 0.10),
    ),
    "mild_ira": Scenario(
        name="mild_ira",
        label="温和本地内容（IRA 式）",
        description=(
            "中等强度本地内容与关税激励，矿产保护温和；"
            "气候按 APS。限制激励上升但未进入全面军备。"
        ),
        params=GameParams(
            climate="APS",
            escalate=True,
            tau0=0.22,
            mu0=0.14,
            access0=0.20,
            tau_growth=0.045,
            mu_growth=0.030,
            access_growth=0.028,
            industrial_rent=0.48,
            localization_subsidy=0.42,
            climate_penalty_scale=0.65,
        ),
        r0=0.26,
        f0=0.28,
    ),
    "race_aps": Scenario(
        name="race_aps",
        label="限制竞赛 × APS（基准）",
        description=(
            "基准叙事：电气化扩产竞赛叠加关税、矿产保护与市场准入；"
            "气候目标取 APS。用于刻画「助力转型的政策反而拉低全球装机」的博弈均衡。"
        ),
        params=GameParams(
            climate="APS",
            escalate=True,
            tau0=0.24,
            mu0=0.18,
            access0=0.20,
            tau_growth=0.085,
            mu_growth=0.070,
            access_growth=0.055,
            industrial_rent=0.58,
            localization_subsidy=0.52,
            retaliation_cost=0.28,
            climate_penalty_scale=0.68,
            eta_r=0.30,
            eta_f=0.34,
        ),
        r0=0.30,
        f0=0.32,
        instrument_path=_piecewise_instruments(
            [
                (0.0, (0.24, 0.18, 0.20)),
                (1.0, (0.38, 0.28, 0.30)),
                (2.0, (0.52, 0.40, 0.42)),
                (4.0, (0.70, 0.58, 0.55)),
                (6.0, (0.82, 0.72, 0.68)),
            ]
        ),
    ),
    "race_steps": Scenario(
        name="race_steps",
        label="限制竞赛 × STEPS",
        description="与基准相同的限制竞赛路径，但气候目标与惩罚权重取 STEPS。",
        params=GameParams(
            climate="STEPS",
            escalate=True,
            tau0=0.24,
            mu0=0.18,
            access0=0.20,
            tau_growth=0.085,
            mu_growth=0.070,
            access_growth=0.055,
            industrial_rent=0.58,
            localization_subsidy=0.52,
            climate_penalty_scale=0.55,
            eta_r=0.30,
            eta_f=0.34,
        ),
        r0=0.30,
        f0=0.32,
        instrument_path=_piecewise_instruments(
            [
                (0.0, (0.24, 0.18, 0.20)),
                (1.0, (0.38, 0.28, 0.30)),
                (2.0, (0.52, 0.40, 0.42)),
                (4.0, (0.70, 0.58, 0.55)),
                (6.0, (0.82, 0.72, 0.68)),
            ]
        ),
    ),
    "race_nze": Scenario(
        name="race_nze",
        label="限制竞赛 × NZE",
        description=(
            "最高气候雄心与最强限制竞赛叠加：目标装机最高，"
            "但碎片化效率损失使缺口也最大——悖论最尖锐的情景。"
        ),
        params=GameParams(
            climate="NZE",
            escalate=True,
            tau0=0.24,
            mu0=0.18,
            access0=0.20,
            tau_growth=0.085,
            mu_growth=0.070,
            access_growth=0.055,
            industrial_rent=0.60,
            localization_subsidy=0.52,
            climate_penalty_scale=0.75,
            climate_internalization=0.22,  # 搭便车：高雄心下仍难单独开放
            retaliation_cost=0.30,
            eta_r=0.30,
            eta_f=0.34,
            policy_speed=1.05,
        ),
        r0=0.28,
        f0=0.30,
        instrument_path=_piecewise_instruments(
            [
                (0.0, (0.24, 0.18, 0.20)),
                (1.0, (0.38, 0.28, 0.30)),
                (2.0, (0.52, 0.40, 0.42)),
                (4.0, (0.70, 0.58, 0.55)),
                (6.0, (0.82, 0.72, 0.68)),
            ]
        ),
    ),
    "mineral_hard": Scenario(
        name="mineral_hard",
        label="矿产硬保护冲击",
        description=(
            "关键矿产出口限制骤然抬升（类锂/镍/石墨出口管制），"
            "全球一体化产能支付急剧恶化，碎片化与装机缺口同步放大。"
        ),
        params=GameParams(
            climate="APS",
            escalate=True,
            industrial_rent=0.54,
            localization_subsidy=0.55,
            mineral_friction=0.70,
            eta_mu=0.32,
            climate_penalty_scale=0.70,
        ),
        r0=0.32,
        f0=0.34,
        instrument_path=_piecewise_instruments(
            [
                (0.0, (0.22, 0.20, 0.18)),
                (1.0, (0.35, 0.55, 0.30)),
                (2.0, (0.48, 0.78, 0.42)),
                (4.0, (0.62, 0.88, 0.55)),
                (6.0, (0.72, 0.92, 0.65)),
            ]
        ),
    ),
    "coop_climate": Scenario(
        name="coop_climate",
        label="气候—产业协同治理",
        description=(
            "反事实协同：气候俱乐部式协调降低报复与准入壁垒，"
            "气候惩罚进入政策支付，推动限制份额回落、装机逼近 NZE 目标。"
        ),
        params=GameParams(
            climate="NZE",
            escalate=False,
            tau0=0.16,
            mu0=0.12,
            access0=0.12,
            industrial_rent=0.30,
            localization_subsidy=0.22,
            open_scale_gain=0.55,
            climate_penalty_scale=0.95,
            climate_internalization=0.90,  # 气候俱乐部抬高内化份额
            retaliation_cost=0.45,
            political_capture=0.08,
            policy_speed=1.15,
            industry_speed=1.05,
        ),
        r0=0.30,
        f0=0.30,
        instrument_path=_piecewise_instruments(
            [
                (0.0, (0.30, 0.22, 0.24)),
                (1.5, (0.22, 0.16, 0.18)),
                (3.0, (0.15, 0.12, 0.12)),
                (5.0, (0.12, 0.10, 0.10)),
            ]
        ),
    ),
}


def run_scenario(scenario: Scenario, t_end: float = 7.0) -> Trajectory:
    game = BatteryPolicyGame(scenario.params)
    return game.simulate(
        r0=scenario.r0,
        f0=scenario.f0,
        t_span=(0.0, t_end),
        n_steps=701,
        label=scenario.label,
        instrument_path=scenario.instrument_path,
    )


def run_all_scenarios(names: list[str] | None = None) -> dict[str, Trajectory]:
    keys = names or list(SCENARIOS.keys())
    return {k: run_scenario(SCENARIOS[k]) for k in keys}


def calibration_targets() -> dict[str, float | str]:
    """公开口径锚点（IEA Global EV Outlook 脉络，取中枢近似）。"""
    return {
        "2023_base_gwh": 750.0,
        "2030_steps_gwh": 750.0 * 4.5,
        "2030_aps_gwh": 750.0 * 5.0,
        "2030_nze_gwh": 750.0 * 7.0,
        "note": "目标装机为情景需求上界；博弈均衡给出经摩擦折损后的实际装机。",
    }
