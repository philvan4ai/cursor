"""
国产 AI 芯片 vs 英伟达：非对称演化博弈模型

两群体：
  - 中国 AI 厂商：策略 {国产栈 D, 英伟达栈 N}，份额 x = 选国产的比例
  - 国产芯片供给侧：策略 {高强度投入 H, 低强度投入 L}，份额 y = 选 H 的比例

美方出口管制强度 σ ∈ [0, 1] 作为外生政策参数，进入双方支付。
EUV/先进制程约束通过产能天花板 κ(t) 限制可支撑的国产化上限，
从而在无 EUV 时形成内点演化稳定策略（ESS），而非角点 100%。

复制者动力学：
  ẋ = x (1 - x) [π_D(x, y; σ) - π_N(x, y; σ)]
  ẏ = y (1 - y) [π_H(x, y; σ, κ) - π_L(x, y; σ, κ)]
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable

import numpy as np
from numpy.typing import NDArray


@dataclass(frozen=True)
class GameParams:
    """模型参数（可校准到公开替代率轨迹）。"""

    # --- AI 厂商支付 ---
    nvidia_base: float = 0.92
    domestic_base: float = 0.48
    domestic_rd_gain: float = 0.36  # 随 y 提升的国产性能/生态增益
    cuda_lockin: float = 0.30  # CUDA 锁定（随 1-x 增强）
    domestic_network: float = 0.22  # 国产安装基数网络效应
    switch_cost: float = 0.18
    supply_risk: float = 0.70  # 管制对英伟达有效支付的惩罚
    forced_migration: float = 0.52  # 管制对国产采用的推力
    subsidy: float = 0.08
    # 产能/先进性拥挤：x 逼近 κ 时国产支付急剧下降 → 内点 ESS
    congestion_scale: float = 1.40
    # 无 EUV 时前沿训练残留给英伟达的利基（随 x 上升而更突出）
    frontier_residual: float = 0.55

    # --- 芯片供给侧支付 ---
    rd_cost_high: float = 0.20
    rd_cost_low: float = 0.05
    demand_reward: float = 0.50
    learning_spillover: float = 0.16
    wall_corner_boost: float = 0.40
    option_value: float = 0.22

    # --- EUV / 制程约束 ---
    euv_breakthrough: bool = False
    kappa0: float = 0.68
    kappa_euv: float = 0.97
    kappa_growth: float = 0.022  # 堆叠工艺缓慢抬升；2030 约 0.88 封顶前

    # --- 动力学 ---
    adopter_speed: float = 1.10
    supplier_speed: float = 1.05
    noise: float = 0.008  # 少量探索/试点，避免角点吸收

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Trajectory:
    t: NDArray[np.floating]
    x: NDArray[np.floating]
    y: NDArray[np.floating]
    kappa: NDArray[np.floating]
    sigma: NDArray[np.floating]
    nvidia_share: NDArray[np.floating]
    params: GameParams
    label: str


class EvolutionaryChipGame:
    """非对称两群体演化博弈 + 管制外生路径。"""

    def __init__(self, params: GameParams | None = None):
        self.params = params or GameParams()

    def kappa(self, t: float) -> float:
        p = self.params
        if p.euv_breakthrough:
            # 突破后天花板迅速抬升（「秦始皇摸电门」）
            return float(min(0.82 + 0.04 * t, p.kappa_euv))
        return float(min(p.kappa0 + p.kappa_growth * t, 0.88))

    def effective_domestic_perf(self, y: float, t: float) -> float:
        p = self.params
        return p.domestic_base + p.domestic_rd_gain * y * self.kappa(t)

    def payoffs_adopters(
        self, x: float, y: float, sigma: float, t: float
    ) -> tuple[float, float]:
        """返回 (π_D, π_N)。"""
        p = self.params
        kappa = self.kappa(t)
        perf_d = self.effective_domestic_perf(y, t)

        eco_d = p.domestic_network * x + 0.12 * y
        eco_n = p.cuda_lockin * (1.0 - x) * (1.0 - 0.50 * sigma)
        switch = p.switch_cost * (1.0 - x) * (1.0 - 0.70 * sigma)

        # 软天花板：x 相对 κ 的三次拥挤（DUV 产能、先进封装、良率）
        # 使无 EUV 时出现内点 ESS，而非角点全面替代
        ratio = x / max(kappa, 1e-3)
        congestion = p.congestion_scale * (ratio**3)

        # 「被迫迁移」随国产份额上升而衰减（早期推力，不是永久补贴）
        migration = p.forced_migration * sigma * (1.0 - 0.65 * x)

        pi_d = perf_d + eco_d + p.subsidy + migration - switch - congestion
        # 份额越高，剩余英伟达需求越集中于不可替代的前沿训练
        residual = p.frontier_residual * (1.0 - kappa) * (0.15 + 1.10 * x)
        pi_n = (
            p.nvidia_base * (1.0 - 0.18 * sigma)
            + eco_n
            - p.supply_risk * sigma * (1.0 - 0.35 * x)
            + residual
        )
        return pi_d, pi_n

    def payoffs_suppliers(
        self, x: float, y: float, sigma: float, t: float
    ) -> tuple[float, float]:
        """返回 (π_H, π_L)。"""
        p = self.params
        kappa = self.kappa(t)
        quality = kappa * (0.40 + 0.60 * y)

        pi_h = (
            p.demand_reward * x * quality
            + p.wall_corner_boost * sigma
            + p.option_value * sigma * (1.0 - 0.25 * x)
            + p.learning_spillover * y
            - p.rd_cost_high * (1.0 - 0.30 * sigma)
        )
        pi_l = (
            p.demand_reward * x * 0.20 * kappa
            + 0.04 * (1.0 - sigma)
            - p.rd_cost_low
        )
        return pi_h, pi_l

    def replicator_rhs(
        self, state: NDArray[np.floating], t: float, sigma: float
    ) -> NDArray[np.floating]:
        x, y = float(state[0]), float(state[1])
        x = float(np.clip(x, 1e-9, 1.0 - 1e-9))
        y = float(np.clip(y, 1e-9, 1.0 - 1e-9))

        pi_d, pi_n = self.payoffs_adopters(x, y, sigma, t)
        pi_h, pi_l = self.payoffs_suppliers(x, y, sigma, t)

        p = self.params
        dx = p.adopter_speed * x * (1.0 - x) * (pi_d - pi_n)
        dy = p.supplier_speed * y * (1.0 - y) * (pi_h - pi_l)

        if p.noise > 0:
            dx += p.noise * (0.5 - x)
            dy += p.noise * (0.5 - y)

        return np.array([dx, dy], dtype=float)

    def simulate(
        self,
        x0: float,
        y0: float,
        t_span: tuple[float, float] = (0.0, 9.0),
        n_steps: int = 900,
        sigma_path: Callable[[float], float] | float = 0.5,
        label: str = "baseline",
    ) -> Trajectory:
        """向前欧拉积分复制者动力学。t 单位：年，2021→2030 ↔ t∈[0,9]。"""
        t = np.linspace(t_span[0], t_span[1], n_steps)
        dt = t[1] - t[0]
        x = np.zeros(n_steps)
        y = np.zeros(n_steps)
        kappa = np.zeros(n_steps)
        sigma_arr = np.zeros(n_steps)

        x[0], y[0] = x0, y0
        sigma_fn = (
            (lambda _t: float(sigma_path))
            if isinstance(sigma_path, (int, float))
            else sigma_path
        )

        for i in range(n_steps - 1):
            sig = float(np.clip(sigma_fn(t[i]), 0.0, 1.0))
            sigma_arr[i] = sig
            kappa[i] = self.kappa(t[i])
            rhs = self.replicator_rhs(np.array([x[i], y[i]]), t[i], sig)
            x[i + 1] = float(np.clip(x[i] + dt * rhs[0], 0.0, 1.0))
            y[i + 1] = float(np.clip(y[i] + dt * rhs[1], 0.0, 1.0))

        sigma_arr[-1] = float(np.clip(sigma_fn(t[-1]), 0.0, 1.0))
        kappa[-1] = self.kappa(t[-1])

        return Trajectory(
            t=t,
            x=x,
            y=y,
            kappa=kappa,
            sigma=sigma_arr,
            nvidia_share=1.0 - x,
            params=self.params,
            label=label,
        )

    def phase_grid(
        self,
        sigma: float,
        t: float = 4.0,
        n: int = 21,
    ) -> tuple[NDArray[np.floating], NDArray[np.floating], NDArray[np.floating], NDArray[np.floating]]:
        xs = np.linspace(0.02, 0.98, n)
        ys = np.linspace(0.02, 0.98, n)
        X, Y = np.meshgrid(xs, ys)
        dX = np.zeros_like(X)
        dY = np.zeros_like(Y)
        for i in range(n):
            for j in range(n):
                rhs = self.replicator_rhs(np.array([X[i, j], Y[i, j]]), t, sigma)
                dX[i, j], dY[i, j] = rhs[0], rhs[1]
        return X, Y, dX, dY

    def find_interior_equilibria(
        self, sigma: float, t: float = 4.0, n: int = 40
    ) -> list[tuple[float, float]]:
        xs = np.linspace(0.05, 0.95, n)
        ys = np.linspace(0.05, 0.95, n)
        hits: list[tuple[float, float]] = []
        for xv in xs:
            for yv in ys:
                rhs = self.replicator_rhs(np.array([xv, yv]), t, sigma)
                if abs(rhs[0]) < 0.012 and abs(rhs[1]) < 0.012:
                    hits.append((round(xv, 2), round(yv, 2)))
        uniq: list[tuple[float, float]] = []
        for h in hits:
            if not any(abs(h[0] - u[0]) < 0.06 and abs(h[1] - u[1]) < 0.06 for u in uniq):
                uniq.append(h)
        return uniq
