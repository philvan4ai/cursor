#!/usr/bin/env python3
"""运行全部情景仿真，导出 CSV / JSON / 图表 / 摘要。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.scenarios import SCENARIOS, calibration_targets, run_all_scenarios
from src.visualize import render_all, year_axis


def trajectory_to_frame(name: str, tr) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "scenario": name,
            "year": year_axis(tr.t),
            "t": tr.t,
            "restrict_share": tr.r,
            "fragment_share": tr.f,
            "open_share": tr.open_share,
            "tau": tr.tau,
            "mu": tr.mu,
            "access": tr.access,
            "q_star_gwh": tr.q_star,
            "q_real_gwh": tr.q_real,
            "eta": tr.eta,
            "gap_gwh": tr.gap,
        }
    )


def snapshot(tr, year: float) -> dict[str, float]:
    idx = int(np.argmin(np.abs(year_axis(tr.t) - year)))
    return {
        "year": year,
        "restrict_share": float(tr.r[idx]),
        "fragment_share": float(tr.f[idx]),
        "open_share": float(tr.open_share[idx]),
        "tau": float(tr.tau[idx]),
        "mu": float(tr.mu[idx]),
        "access": float(tr.access[idx]),
        "q_star_gwh": float(tr.q_star[idx]),
        "q_real_gwh": float(tr.q_real[idx]),
        "eta": float(tr.eta[idx]),
        "gap_gwh": float(tr.gap[idx]),
        "gap_ratio": float(tr.gap[idx] / max(tr.q_star[idx], 1e-9)),
    }


def main() -> None:
    out_dir = ROOT / "output"
    fig_dir = ROOT / "figures"
    out_dir.mkdir(parents=True, exist_ok=True)
    fig_dir.mkdir(parents=True, exist_ok=True)

    traj = run_all_scenarios()
    frames = [trajectory_to_frame(k, tr) for k, tr in traj.items()]
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(out_dir / "trajectories.csv", index=False)

    summary: dict = {
        "logic_chain_paragraph": (
            "在能源转型进程中，动力电池构成电气化路径的核心约束：交通与电力系统脱碳都高度依赖电池装机规模的快速扩张，"
            "因而各国竞相发展动力电池产业、提高产量，本意是为能源转型提供物质基础。然而，产量扩张很快转化为对产业链主导权"
            "与市场竞争优势的争夺，关税、关键矿产保护、市场准入与本地内容等限制性产业政策随之密集出台；这些工具在一国尺度上"
            "可强化本土产能与安全收益，但在全球尺度上会推高成本、分割供应链并压低有效供给。于是出现政策悖论——原本服务于"
            "电气化与气候减缓的政策组合，经战略性互动后反而可能削弱全球动力电池产量与装机能力，使实际部署偏离气候变化控制"
            "目标所需轨迹。本文据此构建非对称演化博弈模型，刻画主要经济体在「开放合作 / 保护限制」与产业侧「全球一体化 / "
            "碎片化本地化」之间的策略演化，并在 IEA 口径的 STEPS、APS、NZE 等气候情景下求解博弈平衡点，定量回答：各国互动"
            "收敛后，全球究竟能实现多少动力电池装机量，以及该均衡装机与各气候情景目标装机之间的缺口有多大。"
        ),
        "logic_chain_steps": [
            "能源转型 → 动力电池成为核心约束",
            "各国扩产以支撑电气化并争夺产业优势",
            "关税 / 矿产保护 / 市场准入等限制政策",
            "供应链碎片化，全球有效产量与装机下降",
            "博弈均衡装机 < 气候情景所需装机（政策悖论）",
        ],
        "calibration_targets": calibration_targets(),
        "scenarios": {},
        "equilibria_2030": {},
    }
    for name, tr in traj.items():
        sc = SCENARIOS[name]
        snaps = {
            "2023": snapshot(tr, 2023),
            "2025": snapshot(tr, 2025),
            "2030": snapshot(tr, 2030),
        }
        summary["scenarios"][name] = {
            "label": sc.label,
            "description": sc.description,
            "climate": sc.params.climate,
            "params": sc.params.to_dict(),
            "snapshots": snaps,
        }
        s2030 = snaps["2030"]
        summary["equilibria_2030"][name] = {
            "label": sc.label,
            "climate": sc.params.climate,
            "restrict_share": s2030["restrict_share"],
            "fragment_share": s2030["fragment_share"],
            "q_star_twh": s2030["q_star_gwh"] / 1000.0,
            "q_real_twh": s2030["q_real_gwh"] / 1000.0,
            "gap_twh": s2030["gap_gwh"] / 1000.0,
            "gap_ratio": s2030["gap_ratio"],
            "eta": s2030["eta"],
        }

    # 基准悖论度量：race_nze 相对 open_nze 的缺口放大
    race = snapshot(traj["race_nze"], 2030)
    open_ = snapshot(traj["open_nze"], 2030)
    summary["paradox_metrics"] = {
        "race_nze_gap_twh": race["gap_gwh"] / 1000.0,
        "open_nze_gap_twh": open_["gap_gwh"] / 1000.0,
        "extra_gap_from_restriction_twh": (race["gap_gwh"] - open_["gap_gwh"]) / 1000.0,
        "race_nze_q_real_twh": race["q_real_gwh"] / 1000.0,
        "open_nze_q_real_twh": open_["q_real_gwh"] / 1000.0,
        "installation_loss_ratio": 1.0 - race["q_real_gwh"] / max(open_["q_real_gwh"], 1e-9),
    }

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    paths = render_all(fig_dir)
    summary["figures"] = {k: str(v.relative_to(ROOT)) for k, v in paths.items()}
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("=== 研究A：动力电池政策博弈仿真完成 ===")
    print(f"CSV:  {out_dir / 'trajectories.csv'}")
    print(f"JSON: {out_dir / 'summary.json'}")
    for k, p in paths.items():
        print(f"FIG:  {p}")
    print("--- 2030 均衡装机 (TWh) ---")
    for name, eq in summary["equilibria_2030"].items():
        print(
            f"{name:14s}  Q*={eq['q_star_twh']:.2f}  Q={eq['q_real_twh']:.2f}  "
            f"gap={eq['gap_twh']:.2f} ({eq['gap_ratio']:.0%})  "
            f"r={eq['restrict_share']:.0%}  f={eq['fragment_share']:.0%}"
        )
    pm = summary["paradox_metrics"]
    print(
        f"悖论：限制竞赛相对开放合作，NZE 下额外缺口 "
        f"{pm['extra_gap_from_restriction_twh']:.2f} TWh，"
        f"装机损失约 {pm['installation_loss_ratio']:.0%}"
    )


if __name__ == "__main__":
    main()
