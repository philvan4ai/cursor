"""绘图：轨迹、相平面、气候情景对比、政策悖论、装机校准。"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import font_manager

from .model import BatteryPolicyGame, Trajectory
from .scenarios import SCENARIOS, run_all_scenarios, run_scenario


def _setup_style() -> None:
    candidates = [
        "WenQuanYi Micro Hei",
        "Noto Sans CJK SC",
        "Source Han Sans SC",
        "Droid Sans Fallback",
        "SimHei",
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
    return 2023.0 + t


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
        label = SCENARIOS[k].label if k in SCENARIOS else tr.label
        ax.plot(year_axis(tr.t), tr.r * 100, label=label)
    ax.set_title("限制政策份额 r(t)")
    ax.set_ylabel("%")
    ax.legend(fontsize=6.5, loc="best")

    ax = axes[0, 1]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.f * 100, label=k)
    ax.set_title("碎片化产能份额 f(t)")
    ax.set_ylabel("%")

    ax = axes[1, 0]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.q_real / 1000.0, label=k)
    ax.set_title("实际装机量 Q(t)")
    ax.set_ylabel("TWh")
    ax.set_xlabel("年")

    ax = axes[1, 1]
    for k in keys:
        tr = trajectories[k]
        ax.plot(year_axis(tr.t), tr.gap / 1000.0, label=k)
    ax.set_title("气候装机缺口 Q*−Q")
    ax.set_ylabel("TWh")
    ax.set_xlabel("年")

    fig.suptitle("研究A：动力电池政策博弈情景对比", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_phase_portrait(out: Path, t: float = 4.0) -> Path:
    _setup_style()
    game = BatteryPolicyGame(SCENARIOS["race_aps"].params)
    # 使用基准情景的工具路径快照
    tau, mu, access = SCENARIOS["race_aps"].instrument_path(t)  # type: ignore[misc]
    game.policy_instruments = lambda _t, v=(tau, mu, access): v  # type: ignore[method-assign]

    R, F, dR, dF = game.phase_grid(t=t, n=18)

    fig, ax = plt.subplots(figsize=(7, 6))
    speed = np.sqrt(dR**2 + dF**2) + 1e-9
    ax.streamplot(R, F, dR, dF, color=speed, cmap="viridis", density=1.2, linewidth=1.0)

    for r0, f0, c in [(0.2, 0.2, "white"), (0.35, 0.4, "orange"), (0.55, 0.55, "cyan")]:
        tr = game.simulate(
            r0=r0,
            f0=f0,
            t_span=(t, t + 3),
            n_steps=300,
            label="sample",
            instrument_path=lambda _t, v=(tau, mu, access): v,
        )
        ax.plot(tr.r, tr.f, color=c, lw=2, alpha=0.9)
        ax.scatter([r0], [f0], color=c, s=40, zorder=5)

    eqs = game.find_interior_equilibria(t=t)
    for eq in eqs:
        ax.scatter([eq[0]], [eq[1]], marker="*", s=160, color="red", zorder=6)

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xlabel("限制政策份额 r")
    ax.set_ylabel("碎片化产能份额 f")
    ax.set_title(f"相平面（APS 限制竞赛, t≈{2023+t:.0f}）")
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_policy_paradox(out: Path) -> Path:
    """展示「助力转型的限制政策」如何拉大气候装机缺口。"""
    _setup_style()
    open_nze = run_scenario(SCENARIOS["open_nze"])
    race_nze = run_scenario(SCENARIOS["race_nze"])
    coop = run_scenario(SCENARIOS["coop_climate"])

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    ax.plot(year_axis(open_nze.t), open_nze.q_star / 1000, "k--", lw=1.5, label="NZE 目标 Q*")
    ax.plot(year_axis(open_nze.t), open_nze.q_real / 1000, lw=2, label="开放合作")
    ax.plot(year_axis(race_nze.t), race_nze.q_real / 1000, lw=2, label="限制竞赛")
    ax.plot(year_axis(coop.t), coop.q_real / 1000, lw=2, label="协同治理")
    ax.set_title("NZE 下实际装机 vs 目标")
    ax.set_ylabel("TWh")
    ax.set_xlabel("年")
    ax.legend(fontsize=8)

    ax = axes[1]
    ax.plot(year_axis(open_nze.t), open_nze.gap / 1000, lw=2, label="开放合作缺口")
    ax.plot(year_axis(race_nze.t), race_nze.gap / 1000, lw=2, label="限制竞赛缺口")
    ax.plot(year_axis(coop.t), coop.gap / 1000, lw=2, label="协同治理缺口")
    ax.set_title("政策悖论：缺口被限制竞赛放大")
    ax.set_ylabel("TWh")
    ax.set_xlabel("年")
    ax.legend(fontsize=8)

    fig.suptitle("研究A核心悖论：限制政策 vs 气候装机目标", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_climate_equilibria(out: Path) -> Path:
    """不同气候情景下的博弈均衡装机。"""
    _setup_style()
    keys = ["race_steps", "race_aps", "race_nze", "open_steps", "open_nze", "coop_climate"]
    traj = {k: run_scenario(SCENARIOS[k]) for k in keys}

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))

    ax = axes[0]
    for k in ["race_steps", "race_aps", "race_nze"]:
        tr = traj[k]
        ax.plot(year_axis(tr.t), tr.q_real / 1000, lw=2, label=SCENARIOS[k].label)
        ax.plot(year_axis(tr.t), tr.q_star / 1000, ls="--", lw=1, alpha=0.7)
    ax.set_title("限制竞赛：实际装机（实线）与目标（虚线）")
    ax.set_ylabel("TWh")
    ax.set_xlabel("年")
    ax.legend(fontsize=7)

    ax = axes[1]
    labels = []
    q_reals = []
    q_stars = []
    for k in ["race_steps", "race_aps", "race_nze", "open_nze", "coop_climate"]:
        tr = traj[k]
        labels.append(SCENARIOS[k].label)
        q_reals.append(tr.q_real[-1] / 1000)
        q_stars.append(tr.q_star[-1] / 1000)
    x = np.arange(len(labels))
    w = 0.36
    ax.bar(x - w / 2, q_stars, w, label="目标 Q*(2030)", color="#8c8c8c")
    ax.bar(x + w / 2, q_reals, w, label="均衡装机 Q(2030)", color="#2a6f97")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=25, ha="right", fontsize=7)
    ax.set_ylabel("TWh")
    ax.set_title("2030 博弈均衡装机对比")
    ax.legend(fontsize=8)

    fig.suptitle("不同气候情景下的博弈平衡点", fontsize=13)
    fig.tight_layout()
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    return out


def plot_calibration(out: Path) -> Path:
    _setup_style()
    steps = run_scenario(SCENARIOS["open_steps"])
    aps = run_scenario(SCENARIOS["race_aps"])
    nze = run_scenario(SCENARIOS["open_nze"])

    fig, ax = plt.subplots(figsize=(8.5, 4.8))
    ax.plot(year_axis(steps.t), steps.q_star / 1000, lw=2, label="STEPS 目标")
    ax.plot(year_axis(aps.t), aps.q_star / 1000, lw=2, label="APS 目标")
    ax.plot(year_axis(nze.t), nze.q_star / 1000, lw=2, label="NZE 目标")
    ax.scatter(
        [2023, 2030, 2030, 2030],
        [0.75, 0.75 * 4.5, 0.75 * 5.0, 0.75 * 7.0],
        s=55,
        zorder=5,
        color="crimson",
        label="IEA 中枢锚点",
    )
    ax.annotate("750 GWh", (2023, 0.75), textcoords="offset points", xytext=(6, 6), fontsize=8)
    ax.annotate("STEPS×4.5", (2030, 0.75 * 4.5), textcoords="offset points", xytext=(-55, 8), fontsize=8)
    ax.annotate("APS×5", (2030, 0.75 * 5.0), textcoords="offset points", xytext=(6, 0), fontsize=8)
    ax.annotate("NZE×7", (2030, 0.75 * 7.0), textcoords="offset points", xytext=(6, -10), fontsize=8)
    ax.set_xlabel("年")
    ax.set_ylabel("TWh")
    ax.set_title("气候情景目标装机路径校准（IEA 倍率）")
    ax.legend(fontsize=8)
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
            keys=[
                "open_steps",
                "open_nze",
                "mild_ira",
                "race_aps",
                "race_steps",
                "race_nze",
                "mineral_hard",
                "coop_climate",
            ],
        ),
        "phase": plot_phase_portrait(fig_dir / "phase_portrait.png"),
        "paradox": plot_policy_paradox(fig_dir / "policy_paradox.png"),
        "climate": plot_climate_equilibria(fig_dir / "climate_equilibria.png"),
        "calibration": plot_calibration(fig_dir / "calibration.png"),
    }
    return paths
