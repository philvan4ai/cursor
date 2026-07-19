from __future__ import annotations

from typing import Any, Sequence

from framework.common.models import FactorEvalResult, FactorMeta
from framework.factor_screening.config import FactorScreeningConfig
from framework.factor_screening.evaluator import (
    FactorEvaluator,
    compress_by_correlation,
)
from framework.factor_screening.synthesis import IntelligentFactorSynthesizer
from framework.factor_screening.synthesis_config import SynthesisConfig


class FactorScreeningPipeline:
    """
    因子筛选编排：
    单因子评估 →（可选）FDR 校正 → 相关性压缩 → 输出入选清单。
    可选：对入选因子做智能合成并再验收。
    """

    def __init__(
        self,
        config: FactorScreeningConfig | None = None,
        synthesis_config: SynthesisConfig | None = None,
    ) -> None:
        self.config = config or FactorScreeningConfig()
        self.evaluator = FactorEvaluator(self.config)
        self.synthesizer = IntelligentFactorSynthesizer(synthesis_config)

    def run(
        self,
        factor_metas: Sequence[FactorMeta],
        rank_ic_map: dict[str, Sequence[float]],
        coverage_map: dict[str, float],
        turnover_map: dict[str, float],
        corr_matrix: dict[tuple[str, str], float] | None = None,
        p_values: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        evaluations: list[FactorEvalResult] = []
        for meta in factor_metas:
            fid = meta.factor_id
            result = self.evaluator.evaluate(
                factor_id=fid,
                rank_ic_series=rank_ic_map.get(fid, []),
                coverage=coverage_map.get(fid, 0.0),
                turnover=turnover_map.get(fid, 1.0),
            )
            # 方向一致性：若配置方向为负，RankIC 取反后再判断符号稳健性
            if meta.direction < 0:
                result.rank_ic_mean *= -1
                result.icir *= -1
            evaluations.append(result)

        if p_values:
            survived = FactorEvaluator.benjamini_hochberg(
                p_values, self.config.fdr_alpha
            )
            for ev in evaluations:
                if ev.factor_id not in survived:
                    ev.passed = False
                    ev.reason = (ev.reason + ";fdr_rejected").strip(";")

        selected = compress_by_correlation(
            evaluations,
            corr_matrix=corr_matrix or {},
            max_corr=self.config.max_corr,
            prefer_higher_icir=self.config.prefer_higher_icir,
        )

        meta_by_id = {m.factor_id: m for m in factor_metas}
        selected_payload = []
        for ev in selected:
            meta = meta_by_id[ev.factor_id]
            selected_payload.append(
                {
                    **meta.to_dict(),
                    "rank_ic_mean": ev.rank_ic_mean,
                    "icir": ev.icir,
                    "coverage": ev.coverage,
                    "turnover": ev.turnover,
                }
            )

        return {
            "config": self.config.to_dict(),
            "evaluations": [e.to_dict() for e in evaluations],
            "selected_factors": selected_payload,
            "selected_ids": [x["factor_id"] for x in selected_payload],
        }

    def run_with_synthesis(
        self,
        factor_metas: Sequence[FactorMeta],
        rank_ic_map: dict[str, Sequence[float]],
        coverage_map: dict[str, float],
        turnover_map: dict[str, float],
        corr_matrix: dict[tuple[str, str], float] | None = None,
        p_values: dict[str, float] | None = None,
        prev_weights: dict[str, float] | None = None,
        factor_values: dict[str, dict[str, float]] | None = None,
        recipe_version: str = "syn-v1",
    ) -> dict[str, Any]:
        """筛选 + 智能合成一体流水线。"""
        screening = self.run(
            factor_metas=factor_metas,
            rank_ic_map=rank_ic_map,
            coverage_map=coverage_map,
            turnover_map=turnover_map,
            corr_matrix=corr_matrix,
            p_values=p_values,
        )
        selected = screening["selected_factors"]
        if not selected:
            return {
                **screening,
                "synthesis": {
                    "accepted": False,
                    "reason": "no_selected_factors",
                    "weights": {},
                },
            }

        factor_icir = {f["factor_id"]: f["icir"] for f in selected}
        factor_ic_series = {
            f["factor_id"]: rank_ic_map.get(f["factor_id"], []) for f in selected
        }
        synthesis = self.synthesizer.run(
            factor_icir=factor_icir,
            factor_ic_series=factor_ic_series,
            corr_matrix=corr_matrix,
            prev_weights=prev_weights,
            factor_values=factor_values,
            recipe_version=recipe_version,
        )
        return {**screening, "synthesis": synthesis}
