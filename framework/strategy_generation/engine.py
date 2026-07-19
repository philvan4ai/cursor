from __future__ import annotations

from typing import Any, Sequence

from framework.common.models import StrategySpec, TargetPosition
from framework.strategy_generation.config import StrategyGenerationConfig


class StrategyGenerationEngine:
    """
    策略生成：
    ICIR 加权信号合成 → 分位数选股 → 行业/单票约束 → 输出策略规格与目标权重。
    """

    def __init__(self, config: StrategyGenerationConfig | None = None) -> None:
        self.config = config or StrategyGenerationConfig()

    @staticmethod
    def synthesize_weights(factor_icir: dict[str, float]) -> dict[str, float]:
        """按 |ICIR| 归一化得到可解释线性权重。"""
        abs_sum = sum(abs(v) for v in factor_icir.values())
        if abs_sum <= 1e-12:
            n = len(factor_icir) or 1
            return {k: 1.0 / n for k in factor_icir}
        return {k: abs(v) / abs_sum for k, v in factor_icir.items()}

    def build_spec(
        self,
        strategy_id: str,
        version: str,
        factor_icir: dict[str, float],
        notes: str = "",
    ) -> StrategySpec:
        weights = self.synthesize_weights(factor_icir)
        return StrategySpec(
            strategy_id=strategy_id,
            version=version,
            universe=self.config.universe,
            factors=list(weights.keys()),
            factor_weights=weights,
            rebalance=self.config.rebalance,
            long_quantile=self.config.long_quantile,
            short_quantile=self.config.short_quantile,
            max_name_weight=self.config.max_name_weight,
            max_industry_weight=self.config.max_industry_weight,
            max_turnover=self.config.max_turnover,
            cost_bps=self.config.cost_bps,
            notes=notes,
        )

    def score_symbols(
        self,
        factor_values: dict[str, dict[str, float]],
        factor_weights: dict[str, float],
    ) -> dict[str, float]:
        """
        factor_values: {factor_id: {symbol: value}}
        返回综合得分。
        """
        scores: dict[str, float] = {}
        for fid, weight in factor_weights.items():
            series = factor_values.get(fid, {})
            for symbol, value in series.items():
                scores[symbol] = scores.get(symbol, 0.0) + weight * value
        return scores

    def generate_target_positions(
        self,
        scores: dict[str, float],
        industries: dict[str, str],
    ) -> list[TargetPosition]:
        if not scores:
            return []

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        n_long = max(1, int(len(ranked) * self.config.long_quantile))
        longs = ranked[:n_long]

        raw_weight = 1.0 / n_long
        capped = min(raw_weight, self.config.max_name_weight)

        # 先按单票上限分配，再按行业上限收缩
        industry_load: dict[str, float] = {}
        selected: list[TargetPosition] = []
        for symbol, score in longs:
            industry = industries.get(symbol, "UNKNOWN")
            room = self.config.max_industry_weight - industry_load.get(industry, 0.0)
            if room <= 1e-12:
                continue
            w = min(capped, room)
            industry_load[industry] = industry_load.get(industry, 0.0) + w
            selected.append(
                TargetPosition(
                    symbol=symbol, weight=w, score=score, industry=industry
                )
            )

        total = sum(p.weight for p in selected)
        if total > 1e-12:
            for p in selected:
                p.weight /= total
        return selected

    def estimate_utility(
        self,
        expected_excess: float,
        expected_vol: float,
        expected_turnover: float,
    ) -> float:
        """简化效用：超额 / 波动 - 换手惩罚 - 成本惩罚。"""
        if expected_vol <= 1e-12:
            return float("-inf")
        cost = expected_turnover * (self.config.cost_bps / 10000.0)
        turnover_penalty = max(0.0, expected_turnover - self.config.max_turnover)
        return expected_excess / expected_vol - cost - turnover_penalty

    def run(
        self,
        strategy_id: str,
        version: str,
        factor_icir: dict[str, float],
        factor_values: dict[str, dict[str, float]],
        industries: dict[str, str],
        expected_excess: float,
        expected_vol: float,
        expected_turnover: float,
        notes: str = "",
    ) -> dict[str, Any]:
        spec = self.build_spec(strategy_id, version, factor_icir, notes=notes)
        scores = self.score_symbols(factor_values, spec.factor_weights)
        positions = self.generate_target_positions(scores, industries)
        utility = self.estimate_utility(
            expected_excess, expected_vol, expected_turnover
        )
        accepted = utility >= self.config.min_utility and len(positions) > 0

        return {
            "accepted": accepted,
            "utility": utility,
            "strategy_spec": spec.to_dict(),
            "target_positions": [
                {
                    "symbol": p.symbol,
                    "weight": p.weight,
                    "score": p.score,
                    "industry": p.industry,
                }
                for p in positions
            ],
            "rejection_reason": ""
            if accepted
            else ("utility_below_threshold" if positions else "empty_positions"),
        }
