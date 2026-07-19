#!/usr/bin/env python3
"""端到端演示：因子筛选 → 策略生成 → 净值风控。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from framework.common.models import FactorMeta
from framework.factor_screening import FactorScreeningPipeline
from framework.nav_risk import NavRiskManager
from framework.strategy_generation import StrategyGenerationEngine


def main() -> None:
    metas = [
        FactorMeta("mom_20", "20日动量", "price"),
        FactorMeta("ep", "盈利收益率", "fundamental"),
        FactorMeta("illiq", "非流动性", "microstructure", direction=-1),
    ]
    screening = FactorScreeningPipeline().run(
        factor_metas=metas,
        rank_ic_map={
            "mom_20": [0.03, 0.04, 0.035, 0.045, 0.038],
            "ep": [0.025, 0.03, 0.028, 0.032, 0.027],
            "illiq": [0.02, 0.022, 0.018, 0.024, 0.021],
        },
        coverage_map={"mom_20": 0.96, "ep": 0.9, "illiq": 0.85},
        turnover_map={"mom_20": 0.35, "ep": 0.15, "illiq": 0.25},
        corr_matrix={("mom_20", "ep"): 0.15, ("mom_20", "illiq"): 0.25, ("ep", "illiq"): 0.2},
    )

    selected = screening["selected_factors"]
    factor_icir = {f["factor_id"]: f["icir"] for f in selected}

    # 构造示意截面
    symbols = [f"S{i}" for i in range(1, 21)]
    factor_values = {
        fid: {sym: ((i * (idx + 1)) % 17) / 10.0 for i, sym in enumerate(symbols)}
        for idx, fid in enumerate(factor_icir)
    }
    industries = {sym: ["tech", "fin", "cons", "indu"][i % 4] for i, sym in enumerate(symbols)}

    strategy = StrategyGenerationEngine().run(
        strategy_id="smart_alpha",
        version="0.1.0",
        factor_icir=factor_icir,
        factor_values=factor_values,
        industries=industries,
        expected_excess=0.1,
        expected_vol=0.15,
        expected_turnover=0.22,
        notes="demo strategy from screening output",
    )

    dates = [f"2024-02-{d:02d}" for d in range(1, 16)]
    navs = [1.0]
    for i in range(1, 15):
        # 前高后撤，触发风控
        navs.append(navs[-1] * (1.01 if i < 8 else 0.97))

    risk = NavRiskManager().run(dates, navs, current_exposure=1.0)

    payload = {
        "selected_factor_ids": screening["selected_ids"],
        "strategy_accepted": strategy["accepted"],
        "strategy_id": strategy["strategy_spec"]["strategy_id"],
        "n_positions": len(strategy["target_positions"]),
        "risk_level": None if risk["latest_event"] is None else risk["latest_event"]["level"],
        "exposure_after": risk["exposure_after"],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
