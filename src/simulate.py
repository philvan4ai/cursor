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
        "core_question": (
            "在不同气候情景（STEPS / APS / NZE）下，各国产业政策与电池产能策略互动收敛后，"
            "全球实际能实现多少动力电池装机？与情景目标装机的缺口有多大？"
        ),
        "logic_chain_paragraph": (
            "成功的能源转型对减缓气候变化至关重要，但转型速度高度依赖动力电池装机的快速扩张。"
            "各国为推进电气化大力发展动力电池产业、提高产量；与此同时，为争夺市场竞争优势，又密集出台关税、"
            "关键矿产保护、市场准入与本地内容等限制政策。主流气候情景通常把所需装机量写成外生目标，却较少处理这些"
            "「本意服务转型」的产业政策经策略互动后如何分割供应链、抬高成本并压低全球有效供给。"
            "在这里，我们对最严格的脱碳路径（及 STEPS/APS 对照）展示：一旦允许政策侧在开放与限制之间、"
            "产业侧在全球一体化与碎片化本地化之间演化，博弈均衡下的实际装机可显著低于情景目标；"
            "关键杠杆是关税—矿产—准入摩擦叠加、产业租金私有化与气候收益公共品属性所驱动的限制竞赛。"
            "协同治理虽能把均衡推回接近目标的装机水平，但在缺乏协调时，限制政策本身会成为气候目标的制度性瓶颈。"
        ),
        "logic_chain_steps": [
            "气候转型必要，但依赖动力电池装机扩张",
            "各国扩产同时出台关税/矿产/准入限制政策",
            "既有气候情景忽视政策策略互动与碎片化",
            "博弈均衡给出实际装机 Q 与缺口 Q*-Q",
            "缺乏协调时限制政策成为制度性瓶颈",
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
