"""绘图：轨迹、相平面、情景对比、EUV 天花板。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

from .model import EvolutionaryChipGame, GameParams, Trajectory
from .scenarios import SCENARIOS, run_all_scenarios, run_scenario


def _setup_style() -> None:
    # 优先中文字体，找不到则回退并避免 tofu 过多干扰
    candidates = [
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "WenQuanYi Micro Hei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in candidates:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name]
            break
    plt.rcParams["axes.unicode_minus"] = False
    plt.rcParams["figure.dpi"] = 140
    plt.rcParams["axes.grid"] = True
    plt.rcParams["grid.alpha"] = 0.25


def year_axis(t: np.ndarray) -> np.ndarray:
    return 2021.0 + t


def plot_trajectories(
    trajectories: dict[str, Trajectory],
    out: Path,
    keys: list[str] | None = None,
) -> Path:
    _setup_style()
    keys = keys or list(trajectories.keys())
    fig, axes = plt.subplots(2, 2, figsize=(11, 8))

    ax = axes[0, 0]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.x * 100, label=SCENARIOS[k].label if k in SCENARIOS else tr.label)
    ax.axhline(10, color="gray", ls=":", lw=1)
    ax.axhline(41, color="gray", ls=":", lw=1)
    ax.axhline(75, color="gray", ls=":", lw=1)
    ax.set_title("国产采用率 x(t)")
    ax.set_ylabel("%")
    ax.legend(fontsize=7, loc="best")

    ax = axes[0, 1]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.nvidia_share * 100, label=k)
    ax.set_title("英伟达份额 1−x(t)")
    ax.set_ylabel("%")

    ax = axes[1, 0]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.y * 100, label=k)
    ax.set_title("供给侧高强度投入份额 y(t)")
    ax.set_ylabel("%")
    ax.set_xlabel("年")

    ax = axes[1, 1]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.sigma, label=k)
    ax.set_title("出口管制强度 σ(t)")
    ax.set_xlabel("年")
    ax.set_ylim(-0.05, 1.05)

    fig.suptitle("演化博弈情景对比：国产芯片 vs 英伟达", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_phase_portrait(out: Path, sigma: float = 0.85, t: float = 4.0) -> Path:
    _setup_style()
    game = EvolutionaryChipGame(SCENARIOS["wsj_dilemma"].params)
    X, Y, dX, dY = game.phase_grid(sigma=sigma, t=t, n=18)

    fig, ax = plt.subplots(figsize=(7, 6))
    speed = np.sqrt(dX**2 + dY**2) + 1e-9
    ax.streamplot(X, Y, dX, dY, color=speed, cmap="viridis", density=1.2, linewidth=1.0)

    # 几条样本轨迹
    for x0, y0, c in [(0.1, 0.2, "white"), (0.25, 0.4, "orange"), (0.5, 0.5, "cyan")]:
        tr = game.simulate(
            x0=x0,
            y0=y0,
            t_span=(t, t + 5),
            n_steps=400,
            sigma_path=sigma,
            label="sample",
        )
        ax.plot(tr.x, tr.y, color=c, lw=2, alpha=0.9)
        ax.scatter([x0], [y0], color=c, s=40, zorder=5)

    eqs = game.find_interior_equilibria(sigma=sigma, t=t)
    for eq in eqs:
        ax.scatter([eq[0]], [eq[1]], marker="*", s=160, color="red", zorder=6)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("国产采用率 x")
    ax.set_ylabel("高强度投入 y")
    ax.set_title(f"相平面（σ={sigma:.2f}, t≈{2021+t:.0f}）")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_dilemma_payoff(out: Path) -> Path:
    """展示美方「卖/不卖」两难：短期遏制 vs 长期替代。"""
    _setup_style()
    soft = run_scenario(SCENARIOS["sell_soft"])
    hard = run_scenario(SCENARIOS["hard_ban"])
    none = run_scenario(SCENARIOS["no_control"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    for tr, name in [
        (none, "无管制"),
        (soft, "卖（特供）"),
        (hard, "不卖（围堵）"),
    ]:
        ax.plot(year_axis(tr.t), tr.x * 100, lw=2, label=name)
    ax.set_title("对国产替代的影响")
    ax.set_ylabel("国产采用率 %")
    ax.set_xlabel("年")
    ax.legend()

    ax = axes[1]
    # 「铁拳权威」代理指标：管制强度 × (1 − 国产实际替代进度相对预期)
    # 简化：权威侵蚀 = 国产采用加速相对无管制的超额上升
    for tr, name in [(soft, "卖"), (hard, "不卖")]:
        erosion = (tr.x - none.x) * 100
        ax.plot(year_axis(tr.t), erosion, lw=2, label=f"{name}：超额国产化")
    ax.set_title("「适得其反」度量：相对无管制的超额替代")
    ax.set_ylabel("百分点")
    ax.set_xlabel("年")
    ax.legend()

    fig.suptitle("WSJ 两难的演化博弈刻画", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_euv_ceiling(out: Path) -> Path:
    _setup_style()
    base = run_scenario(SCENARIOS["wsj_dilemma"])
    euv = run_scenario(SCENARIOS["euv_breakthrough"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    ax = axes[0]
    ax.plot(year_axis(base.t), base.kappa, label="DUV+堆叠天花板 κ(t)", lw=2)
    ax.plot(year_axis(euv.t), euv.kappa, label="EUV 突破 κ", lw=2)
    ax.set_ylim(0, 1.05)
    ax.set_title("先进制程约束")
    ax.set_xlabel("年")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(year_axis(base.t), base.x * 100, label="无 EUV", lw=2)
    ax.plot(year_axis(euv.t), euv.x * 100, label="EUV 突破", lw=2)
    ax.set_title("对国产采用率的影响")
    ax.set_ylabel("%")
    ax.set_xlabel("年")
    ax.legend()

    fig.suptitle("命门：EUV 光刻与演化天花板", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_calibration(out: Path) -> Path:
    _setup_style()
    tr = run_scenario(SCENARIOS["wsj_dilemma"])
    years = year_axis(tr.t)
    # 锚点
    anchors_y = [2021, 2025, 2030]
    anchors_v = [10, 41, 75]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    ax.plot(years, tr.x * 100, lw=2.5, label="模型：WSJ 两难路径")
    ax.scatter(anchors_y, anchors_v, s=70, zorder=5, color="crimson", label="公开口径锚点")
    for y, v in zip(anchors_y, anchors_v):
        ax.annotate(f"{v}%", (y, v), textcoords="offset points", xytext=(6, 6), fontsize=9)
    ax.set_xlabel("年")
    ax.set_ylabel("国产替代率 %")
    ax.set_title("基准情景与 10%→41%→75% 轨迹对照")
    ax.legend()
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def render_all(fig_dir: Path) -> dict[str, Path]:
    traj = run_all_scenarios()
    paths = {
        "trajectories": plot_trajectories(
            traj,
            fig_dir / "trajectories.png",
            keys=["no_control", "sell_soft", "wsj_dilemma", "hard_ban", "ascend_shock", "euv_breakthrough"],
        ),
        "phase": plot_phase_portrait(fig_dir / "phase_portrait.png"),
        "dilemma": plot_dilemma_payoff(fig_dir / "dilemma.png"),
        "euv": plot_euv_ceiling(fig_dir / "euv_ceiling.png"),
        "calibration": plot_calibration(fig_dir / "calibration.png"),
    }
    return paths
