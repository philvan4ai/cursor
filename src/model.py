"""
研究A：能源转型中的动力电池政策博弈

逻辑链（形式化）：
  能源转型 → 电气化依赖动力电池 → 各国扩产争夺优势
  → 关税 / 矿产保护 / 市场准入等限制政策
  → 供应链碎片化、成本上升、全球有效产量下降
  → 实际装机量可能达不到气候情景所需装机量

两群体非对称演化博弈：
  - 主要经济体（政策侧）：{开放合作 O, 保护限制 R}，份额 r = 选限制的比例
  - 电池产业（产能侧）：{全球一体化扩张 G, 碎片化本地化 F}，份额 f = 选碎片化的比例

气候情景强度 α ∈ {STEPS, APS, NZE} 同时决定：
  1) 目标装机路径 Q*(t; α)
  2) 气候欠账对限制政策的惩罚权重

复制者动力学：
  ṙ = α_r · r(1−r)[π_R − π_O]
  ḟ = α_f · f(1−f)[π_F − π_G]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray


# IEA 口径锚点（GWh，动力电池为主；2023≈750，情景倍率指向 2030）
CLIMATE_MULTIPLIERS_2030 = {
    "STEPS": 4.5,  # ~3.4 TWh
    "APS": 5.0,  # ~3.8 TWh
    "NZE": 7.0,  # ~5.3 TWh
}

CLIMATE_ALPHA = {
    "STEPS": 0.35,  # 气候惩罚权重较低（现有政策惯性）
    "APS": 0.65,
    "NZE": 1.00,  # 1.5°C/净零路径下欠账代价最大
}


@dataclass(frozen=True)
class GameParams:
    """模型参数：政策租金、气候惩罚、碎片化摩擦与装机映射。"""

    # --- 气候情景 ---
    climate: str = "APS"
    q0_gwh: float = 750.0  # 2023 基准装机/需求

    # --- 政策侧支付 ---
    industrial_rent: float = 0.55  # 限制政策带来的产业租金/就业/话语权
    security_value: float = 0.28  # 战略自主 / 供应链安全收益
    open_scale_gain: float = 0.42  # 开放带来的规模与成本优势
    climate_penalty_scale: float = 0.70  # 装机缺口对限制政策的惩罚
    # 气候收益是全球公共品：各国仅内化一部分（搭便车），协同治理可抬高
    climate_internalization: float = 0.28
    retaliation_cost: float = 0.30  # 贸易报复与市场分割成本
    political_capture: float = 0.18  # 本地产业游说对限制策略的加成

    # --- 产业侧支付 ---
    localization_subsidy: float = 0.48  # 本地内容/准入政策对碎片化的补贴
    scale_economy: float = 0.50  # 全球一体化学习曲线收益
    tariff_friction: float = 0.55  # 关税对全球一体化的打击
    mineral_friction: float = 0.45  # 矿产保护对产能扩张的摩擦
    access_friction: float = 0.40  # 市场准入壁垒摩擦
    duplication_cost: float = 0.35  # 各地重复建厂的效率损失

    # --- 外生摩擦路径缩放 ---
    tau0: float = 0.20  # 关税/本地内容基线
    mu0: float = 0.15  # 矿产保护基线
    access0: float = 0.18  # 市场准入基线
    tau_growth: float = 0.08
    mu_growth: float = 0.06
    access_growth: float = 0.05
    escalate: bool = True  # 是否进入限制政策军备竞赛

    # --- 装机效率映射 η(r,f,τ,μ,a) ---
    eta_r: float = 0.28
    eta_f: float = 0.32
    eta_tau: float = 0.22
    eta_mu: float = 0.20
    eta_access: float = 0.18
    # 限制上升时本地扩产的部分对冲（无法完全抵消全球效率损失）
    localization_offset: float = 0.12

    # --- 动力学 ---
    policy_speed: float = 1.05
    industry_speed: float = 1.10
    noise: float = 0.008

    def to_dict(self) -> dict:
        return asdict(self)

    @property
    def climate_alpha(self) -> float:
        return CLIMATE_ALPHA.get(self.climate, 0.65)

    @property
    def multiplier_2030(self) -> float:
        return CLIMATE_MULTIPLIERS_2030.get(self.climate, 5.0)


@dataclass
class Trajectory:
    t: NDArray[np.floating]
    r: NDArray[np.floating]  # 限制政策份额
    f: NDArray[np.floating]  # 碎片化产能份额
    tau: NDArray[np.floating]
    mu: NDArray[np.floating]
    access: NDArray[np.floating]
    q_star: NDArray[np.floating]
    q_real: NDArray[np.floating]
    eta: NDArray[np.floating]
    gap: NDArray[np.floating]
    open_share: NDArray[np.floating]
    params: GameParams
    label: str


class BatteryPolicyGame:
    """动力电池限制政策 vs 气候装机目标的演化博弈。"""

    def __init__(self, params: GameParams | None = None):
        self.params = params or GameParams()

    def policy_instruments(self, t: float) -> tuple[float, float, float]:
        """返回 (τ, μ, a)：关税、矿产保护、市场准入强度。"""
        p = self.params
        if p.escalate:
            # 政策军备：随时间抬升并饱和
            tau = min(p.tau0 + p.tau_growth * t, 0.95)
            mu = min(p.mu0 + p.mu_growth * t, 0.92)
            access = min(p.access0 + p.access_growth * t, 0.90)
        else:
            tau = p.tau0
            mu = p.mu0
            access = p.access0
        return float(tau), float(mu), float(access)

    def target_installation(self, t: float) -> float:
        """气候情景下的目标装机路径 Q*(t)，单位 GWh。

        t=0 → 2023，t=7 → 2030。采用平滑指数增长逼近 2030 倍率。
        """
        p = self.params
        # Q*(t) = Q0 * m^{t/7}
        growth = p.multiplier_2030 ** (t / 7.0)
        return float(p.q0_gwh * growth)

    def efficiency(
        self, r: float, f: float, tau: float, mu: float, access: float
    ) -> float:
        """全球有效装机效率 η ∈ (0,1]。"""
        p = self.params
        friction = (
            p.eta_r * r
            + p.eta_f * f
            + p.eta_tau * tau
            + p.eta_mu * mu
            + p.eta_access * access
        )
        # 本地化在限制环境下有限对冲，但重复建设仍压效率
        offset = p.localization_offset * f * r
        eta = 1.0 / (1.0 + max(friction - offset, 0.0))
        return float(np.clip(eta, 0.15, 1.0))

    def realized_installation(
        self, r: float, f: float, t: float
    ) -> tuple[float, float, float]:
        """返回 (Q*, Q, η)。"""
        tau, mu, access = self.policy_instruments(t)
        q_star = self.target_installation(t)
        eta = self.efficiency(r, f, tau, mu, access)
        return q_star, q_star * eta, eta

    def payoffs_policy(
        self, r: float, f: float, t: float
    ) -> tuple[float, float]:
        """返回 (π_R, π_O)。"""
        p = self.params
        alpha = p.climate_alpha
        phi = p.climate_internalization  # 公共品内化份额
        tau, mu, access = self.policy_instruments(t)
        q_star, q_real, _ = self.realized_installation(r, f, t)
        gap_ratio = (q_star - q_real) / max(q_star, 1e-6)

        # 限制：产业租金是私有收益；气候欠账仅按 phi 内化 → 易陷入囚徒困境
        pi_r = (
            p.industrial_rent * (0.45 + 0.55 * f)
            + p.security_value * (0.5 * tau + 0.3 * mu + 0.2 * access)
            + p.political_capture * f
            - p.climate_penalty_scale * alpha * phi * gap_ratio
            - p.retaliation_cost * (0.4 * r + 0.35 * tau + 0.25 * mu)
        )

        # 开放：规模收益私有；气候进展亦仅按 phi 内化，故单独开放激励不足
        pi_o = (
            p.open_scale_gain * (1.0 - 0.55 * f) * (1.0 - 0.40 * tau)
            + 0.35 * alpha * phi * (1.0 - gap_ratio)
            - 0.55 * p.industrial_rent * f
            - 0.22 * p.security_value * (1.0 - mu)
        )
        return pi_r, pi_o

    def payoffs_industry(
        self, r: float, f: float, t: float
    ) -> tuple[float, float]:
        """返回 (π_F, π_G)。"""
        p = self.params
        tau, mu, access = self.policy_instruments(t)

        # 碎片化本地化：吃本地补贴与准入红利，但付重复建设成本
        pi_f = (
            p.localization_subsidy * (0.35 + 0.65 * r)
            + 0.25 * access * r
            + 0.15 * mu * r
            - p.duplication_cost * (0.4 + 0.6 * f)
            - 0.12 * (1.0 - r)  # 开放世界里本地化优势弱
        )

        # 全球一体化：吃规模与学习曲线，但被关税/矿产/准入打击
        barrier = (
            p.tariff_friction * tau
            + p.mineral_friction * mu
            + p.access_friction * access
        )
        pi_g = (
            p.scale_economy * (1.0 - 0.50 * f)
            - barrier * (0.55 + 0.45 * r)
            - 0.10 * r
        )
        return pi_f, pi_g

    def replicator_rhs(
        self, state: NDArray[np.floating], t: float
    ) -> NDArray[np.floating]:
        r, f = float(state[0]), float(state[1])
        r = float(np.clip(r, 1e-9, 1.0 - 1e-9))
        f = float(np.clip(f, 1e-9, 1.0 - 1e-9))

        pi_r, pi_o = self.payoffs_policy(r, f, t)
        pi_f, pi_g = self.payoffs_industry(r, f, t)

        p = self.params
        dr = p.policy_speed * r * (1.0 - r) * (pi_r - pi_o)
        df = p.industry_speed * f * (1.0 - f) * (pi_f - pi_g)

        if p.noise > 0:
            dr += p.noise * (0.5 - r)
            df += p.noise * (0.5 - f)

        return np.array([dr, df], dtype=float)

    def simulate(
        self,
        r0: float,
        f0: float,
        t_span: tuple[float, float] = (0.0, 7.0),
        n_steps: int = 701,
        label: str = "baseline",
        instrument_path: Callable[[float], tuple[float, float, float]] | None = None,
    ) -> Trajectory:
        """向前欧拉积分。t 单位：年，2023→2030 ↔ t∈[0,7]。"""
        t = np.linspace(t_span[0], t_span[1], n_steps)
        dt = t[1] - t[0]
        r = np.zeros(n_steps)
        f = np.zeros(n_steps)
        tau_arr = np.zeros(n_steps)
        mu_arr = np.zeros(n_steps)
        access_arr = np.zeros(n_steps)
        q_star = np.zeros(n_steps)
        q_real = np.zeros(n_steps)
        eta_arr = np.zeros(n_steps)

        r[0], f[0] = r0, f0

        # 允许情景覆盖外生工具路径
        original_instruments = self.policy_instruments
        if instrument_path is not None:
            self.policy_instruments = instrument_path  # type: ignore[method-assign]

        try:
            for i in range(n_steps):
                tau, mu, access = self.policy_instruments(t[i])
                tau_arr[i], mu_arr[i], access_arr[i] = tau, mu, access
                qs, qr, eta = self.realized_installation(r[i], f[i], t[i])
                q_star[i], q_real[i], eta_arr[i] = qs, qr, eta
                if i < n_steps - 1:
                    rhs = self.replicator_rhs(np.array([r[i], f[i]]), t[i])
                    r[i + 1] = float(np.clip(r[i] + dt * rhs[0], 0.0, 1.0))
                    f[i + 1] = float(np.clip(f[i] + dt * rhs[1], 0.0, 1.0))
        finally:
            self.policy_instruments = original_instruments  # type: ignore[method-assign]

        return Trajectory(
            t=t,
            r=r,
            f=f,
            tau=tau_arr,
            mu=mu_arr,
            access=access_arr,
            q_star=q_star,
            q_real=q_real,
            eta=eta_arr,
            gap=q_star - q_real,
            open_share=1.0 - r,
            params=self.params,
            label=label,
        )

    def phase_grid(
        self,
        t: float = 4.0,
        n: int = 21,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating], NDArray[np.floating], NDArray[np.floating]]:
        rs = np.linspace(0.02, 0.98, n)
        fs = np.linspace(0.02, 0.98, n)
        R, F = np.meshgrid(rs, fs)
        dR = np.zeros_like(R)
        dF = np.zeros_like(F)
        for i in range(n):
            for j in range(n):
                rhs = self.replicator_rhs(np.array([R[i, j], F[i, j]]), t)
                dR[i, j], dF[i, j] = rhs[0], rhs[1]
        return R, F, dR, dF

    def find_interior_equilibria(
        self, t: float = 4.0, n: int = 40
    ) -> list[tuple[float, float]]:
        rs = np.linspace(0.05, 0.95, n)
        fs = np.linspace(0.05, 0.95, n)
        hits: list[tuple[float, float]] = []
        for rv in rs:
            for fv in fs:
                rhs = self.replicator_rhs(np.array([rv, fv]), t)
                if abs(rhs[0]) < 0.012 and abs(rhs[1]) < 0.012:
                    hits.append((round(rv, 2), round(fv, 2)))
        uniq: list[tuple[float, float]] = []
        for h in hits:
            if not any(abs(h[0] - u[0]) < 0.06 and abs(h[1] - u[1]) < 0.06 for u in uniq):
                uniq.append(h)
        return uniq
