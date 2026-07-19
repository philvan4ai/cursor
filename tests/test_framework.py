from __future__ import annotations

import unittest

from framework.common.models import FactorMeta
from framework.factor_screening import FactorScreeningPipeline
from framework.nav_risk import NavRiskManager
from framework.strategy_generation import StrategyGenerationEngine


class FactorScreeningTests(unittest.TestCase):
    def test_selects_strong_uncorrelated_factors(self) -> None:
        metas = [
            FactorMeta("mom", "动量", "price", direction=1),
            FactorMeta("value", "价值", "fundamental", direction=1),
            FactorMeta("noise", "噪声", "price", direction=1),
        ]
        rank_ic_map = {
            "mom": [0.04, 0.05, 0.03, 0.06, 0.04],
            "value": [0.03, 0.035, 0.028, 0.04, 0.033],
            "noise": [0.001, -0.002, 0.0, 0.001, -0.001],
        }
        coverage = {"mom": 0.95, "value": 0.92, "noise": 0.9}
        turnover = {"mom": 0.3, "value": 0.2, "noise": 0.1}
        corr = {("mom", "value"): 0.2, ("mom", "noise"): 0.1, ("value", "noise"): 0.05}

        result = FactorScreeningPipeline().run(
            metas, rank_ic_map, coverage, turnover, corr_matrix=corr
        )
        self.assertIn("mom", result["selected_ids"])
        self.assertIn("value", result["selected_ids"])
        self.assertNotIn("noise", result["selected_ids"])

    def test_intelligent_synthesis_after_screening(self) -> None:
        metas = [
            FactorMeta("mom", "动量", "price"),
            FactorMeta("value", "价值", "fundamental"),
            FactorMeta("quality", "质量", "fundamental"),
        ]
        rank_ic_map = {
            "mom": [0.04, 0.05, 0.03, 0.06, 0.04],
            "value": [0.03, 0.035, 0.028, 0.04, 0.033],
            "quality": [0.025, 0.03, 0.027, 0.032, 0.029],
        }
        coverage = {"mom": 0.95, "value": 0.92, "quality": 0.9}
        turnover = {"mom": 0.3, "value": 0.2, "quality": 0.15}
        # mom 与 quality 中等相关：可通过筛选，但合成时应受相关惩罚
        corr = {
            ("mom", "value"): 0.15,
            ("mom", "quality"): 0.55,
            ("value", "quality"): 0.2,
        }
        out = FactorScreeningPipeline().run_with_synthesis(
            metas,
            rank_ic_map,
            coverage,
            turnover,
            corr_matrix=corr,
            recipe_version="syn-test-v1",
        )
        self.assertTrue(out["synthesis"]["accepted"])
        weights = out["synthesis"]["weights"]
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=6)
        self.assertEqual(set(weights), {"mom", "value", "quality"})
        # 相关惩罚下，mom 与 quality 合计权重应低于无惩罚时的极端集中
        self.assertLessEqual(max(weights.values()), 0.5 + 1e-6)

class StrategyGenerationTests(unittest.TestCase):
    def test_generates_constrained_positions(self) -> None:
        engine = StrategyGenerationEngine()
        factor_icir = {"mom": 0.8, "value": 0.5}
        factor_values = {
            "mom": {"A": 1.0, "B": 0.5, "C": -0.2, "D": -1.0, "E": 0.8},
            "value": {"A": 0.6, "B": 0.7, "C": 0.1, "D": -0.5, "E": 0.4},
        }
        industries = {"A": "tech", "B": "tech", "C": "fin", "D": "fin", "E": "cons"}

        out = engine.run(
            strategy_id="alpha_core",
            version="0.1.0",
            factor_icir=factor_icir,
            factor_values=factor_values,
            industries=industries,
            expected_excess=0.08,
            expected_vol=0.12,
            expected_turnover=0.2,
        )
        self.assertTrue(out["accepted"])
        self.assertAlmostEqual(
            sum(p["weight"] for p in out["target_positions"]), 1.0, places=6
        )
        self.assertIn("factor_weights", out["strategy_spec"])


class NavRiskTests(unittest.TestCase):
    def test_triggers_deleverage_on_hard_drawdown(self) -> None:
        dates = [f"2024-01-{i:02d}" for i in range(1, 11)]
        # 峰值后回撤约 12%，应触发 L2 降仓
        navs = [1.0, 1.02, 1.05, 1.04, 1.02, 1.0, 0.98, 0.96, 0.94, 0.93]
        manager = NavRiskManager()
        result = manager.run(dates, navs, current_exposure=1.0)
        self.assertIsNotNone(result["peak_event"])
        self.assertEqual(result["peak_event"]["level"], "L2_DELEVERAGE")
        self.assertLess(result["exposure_after"], result["exposure_before"])


if __name__ == "__main__":
    unittest.main()
