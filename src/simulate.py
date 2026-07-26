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
            "domestic_share": tr.x,
            "nvidia_share": tr.nvidia_share,
            "supplier_high_effort": tr.y,
            "sigma": tr.sigma,
            "kappa": tr.kappa,
        }
    )


def snapshot(tr, year: float) -> dict[str, float]:
    idx = int(np.argmin(np.abs(year_axis(tr.t) - year)))
    return {
        "year": year,
        "domestic_share": float(tr.x[idx]),
        "nvidia_share": float(tr.nvidia_share[idx]),
        "y": float(tr.y[idx]),
        "sigma": float(tr.sigma[idx]),
        "kappa": float(tr.kappa[idx]),
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

    summary = {
        "calibration_targets": calibration_targets(),
        "scenarios": {},
    }
    for name, tr in traj.items():
        sc = SCENARIOS[name]
        summary["scenarios"][name] = {
            "label": sc.label,
            "description": sc.description,
            "params": sc.params.to_dict(),
            "snapshots": {
                "2021": snapshot(tr, 2021),
                "2025": snapshot(tr, 2025),
                "2030": snapshot(tr, 2030),
            },
        }

    # 基准校准误差
    base = traj["wsj_dilemma"]
    s2025 = snapshot(base, 2025)["domestic_share"]
    s2030 = snapshot(base, 2030)["domestic_share"]
    summary["wsj_dilemma_fit"] = {
        "domestic_2025": s2025,
        "domestic_2030": s2030,
        "abs_err_2025_vs_41pct": abs(s2025 - 0.41),
        "abs_err_2030_vs_75pct": abs(s2030 - 0.75),
    }

    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    paths = render_all(fig_dir)
    summary["figures"] = {k: str(v.relative_to(ROOT)) for k, v in paths.items()}
    with open(out_dir / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("=== 演化博弈仿真完成 ===")
    print(f"CSV:  {out_dir / 'trajectories.csv'}")
    print(f"JSON: {out_dir / 'summary.json'}")
    for k, p in paths.items():
        print(f"FIG:  {p}")
    fit = summary["wsj_dilemma_fit"]
    print(
        f"基准情景 2025 国产份额={fit['domestic_2025']:.1%} "
        f"(目标41%, |err|={fit['abs_err_2025_vs_41pct']:.1%}); "
        f"2030={fit['domestic_2030']:.1%} "
        f"(目标75%, |err|={fit['abs_err_2030_vs_75pct']:.1%})"
    )


if __name__ == "__main__":
    main()
