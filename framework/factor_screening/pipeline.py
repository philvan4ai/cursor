from __future__ import annotations

from typing import Any, Sequence

from framework.common.models import FactorEvalResult, FactorMeta
from framework.factor_screening.config import FactorScreeningConfig
from framework.factor_screening.evaluator import (
    FactorEvaluator,
    compress_by_correlation,
)


class FactorScreeningPipeline:
    """
    因子筛选编排：
    单因子评估 →（可选）FDR 校正 → 相关性压缩 → 输出入选清单。
    """

    def __init__(self, config: FactorScreeningConfig | None = None) -> None:
        self.config = config or FactorScreeningConfig()
        self.evaluator = FactorEvaluator(self.config)

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
