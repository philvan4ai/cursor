from __future__ import annotations

import math
from typing import Iterable, Sequence

from framework.common.models import FactorEvalResult
from framework.factor_screening.config import FactorScreeningConfig


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    m = _mean(values)
    var = sum((x - m) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


class FactorEvaluator:
    """单因子评估：RankIC / ICIR / 覆盖率 / 换手。"""

    def __init__(self, config: FactorScreeningConfig | None = None) -> None:
        self.config = config or FactorScreeningConfig()

    def evaluate(
        self,
        factor_id: str,
        rank_ic_series: Sequence[float],
        coverage: float,
        turnover: float,
    ) -> FactorEvalResult:
        ic_mean = _mean(list(rank_ic_series))
        ic_std = _std(list(rank_ic_series))
        icir = ic_mean / ic_std if ic_std > 1e-12 else 0.0

        reasons: list[str] = []
        if abs(ic_mean) < self.config.min_abs_rank_ic:
            reasons.append("rank_ic_below_threshold")
        if abs(icir) < self.config.min_icir:
            reasons.append("icir_below_threshold")
        if coverage < self.config.min_coverage:
            reasons.append("coverage_below_threshold")
        if turnover > self.config.max_turnover:
            reasons.append("turnover_above_threshold")

        return FactorEvalResult(
            factor_id=factor_id,
            rank_ic_mean=ic_mean,
            icir=icir,
            coverage=coverage,
            turnover=turnover,
            passed=not reasons,
            reason=";".join(reasons),
        )

    @staticmethod
    def benjamini_hochberg(
        p_values: dict[str, float], alpha: float
    ) -> set[str]:
        """BH-FDR 多重检验，返回通过的因子 ID。"""
        if not p_values:
            return set()
        items = sorted(p_values.items(), key=lambda x: x[1])
        m = len(items)
        cutoff_idx = -1
        for i, (_, p) in enumerate(items, start=1):
            if p <= (i / m) * alpha:
                cutoff_idx = i
        if cutoff_idx < 0:
            return set()
        return {fid for fid, _ in items[:cutoff_idx]}


def compress_by_correlation(
    candidates: Iterable[FactorEvalResult],
    corr_matrix: dict[tuple[str, str], float],
    max_corr: float,
    prefer_higher_icir: bool = True,
) -> list[FactorEvalResult]:
    """按相关性贪心去冗余，优先保留 ICIR 更高者。"""
    ordered = sorted(
        [c for c in candidates if c.passed],
        key=lambda x: abs(x.icir),
        reverse=prefer_higher_icir,
    )
    selected: list[FactorEvalResult] = []
    for cand in ordered:
        ok = True
        max_abs = 0.0
        for kept in selected:
            key = (cand.factor_id, kept.factor_id)
            alt = (kept.factor_id, cand.factor_id)
            corr = abs(corr_matrix.get(key, corr_matrix.get(alt, 0.0)))
            max_abs = max(max_abs, corr)
            if corr > max_corr:
                ok = False
                break
        cand.max_abs_corr_with_selected = max_abs
        if ok:
            selected.append(cand)
        else:
            cand.passed = False
            cand.reason = (cand.reason + ";redundant").strip(";")
    return selected
