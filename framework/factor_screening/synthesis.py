from __future__ import annotations

import math
from typing import Any, Sequence

from framework.factor_screening.synthesis_config import SynthesisConfig


def _clip(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


class IntelligentFactorSynthesizer:
    """
    因子智能合成器（生产优先的可解释线性方案）：

    1) 以 |ICIR| 为预测力先验
    2) 用相关惩罚抑制冗余共振
    3) 施加权重上下限
    4) 可选对上期权重做平滑，控制换手
    5) 输出综合因子与可审计配方
    """

    def __init__(self, config: SynthesisConfig | None = None) -> None:
        self.config = config or SynthesisConfig()

    def _corr(self, corr_matrix: dict[tuple[str, str], float], a: str, b: str) -> float:
        if a == b:
            return 1.0
        return float(corr_matrix.get((a, b), corr_matrix.get((b, a), 0.0)))

    def allocate_weights(
        self,
        factor_icir: dict[str, float],
        corr_matrix: dict[tuple[str, str], float] | None = None,
        prev_weights: dict[str, float] | None = None,
    ) -> dict[str, float]:
        if not factor_icir:
            return {}

        corr_matrix = corr_matrix or {}
        ids = list(factor_icir.keys())
        # 原始分数：ICIR 强度 - 与其他高 ICIR 因子的相关惩罚
        raw: dict[str, float] = {}
        for i in ids:
            strength = abs(factor_icir[i])
            penalty = 0.0
            for j in ids:
                if i == j:
                    continue
                penalty += abs(self._corr(corr_matrix, i, j)) * abs(factor_icir[j])
            score = strength - self.config.corr_penalty * penalty / max(len(ids) - 1, 1)
            raw[i] = max(score, 1e-6)

        total = sum(raw.values())
        weights = {k: v / total for k, v in raw.items()}
        weights = self._project_weights(weights)

        if prev_weights:
            smoothed: dict[str, float] = {}
            s = _clip(self.config.smooth, 0.0, 1.0)
            for k in ids:
                old = prev_weights.get(k, weights[k])
                smoothed[k] = (1.0 - s) * old + s * weights[k]
            total = sum(smoothed.values())
            weights = self._project_weights({k: v / total for k, v in smoothed.items()})

        return weights

    def _project_weights(self, weights: dict[str, float]) -> dict[str, float]:
        """将权重投影到 [min_weight, max_weight] 且归一。"""
        if not weights:
            return {}
        lo, hi = self.config.min_weight, self.config.max_weight
        ids = list(weights.keys())
        # 可行性检查：n*lo <= 1 <= n*hi
        n = len(ids)
        if n * lo > 1.0 + 1e-9 or n * hi < 1.0 - 1e-9:
            # 约束不可行时退化为归一化裁剪
            clipped = {k: _clip(w, lo, hi) for k, w in weights.items()}
            total = sum(clipped.values()) or 1.0
            return {k: v / total for k, v in clipped.items()}

        w = dict(weights)
        fixed: set[str] = set()
        for _ in range(n + 2):
            free = [k for k in ids if k not in fixed]
            # 先把越界的钉住
            changed = False
            for k in list(free):
                if w[k] > hi:
                    w[k] = hi
                    fixed.add(k)
                    changed = True
                elif w[k] < lo:
                    w[k] = lo
                    fixed.add(k)
                    changed = True
            free = [k for k in ids if k not in fixed]
            remain = 1.0 - sum(w[k] for k in fixed)
            if not free:
                break
            free_sum = sum(w[k] for k in free) or 1.0
            for k in free:
                w[k] = remain * (w[k] / free_sum)
            if not changed and all(lo - 1e-12 <= w[k] <= hi + 1e-12 for k in free):
                break

        # 数值清理：保持和为 1，同时尽量贴近边界
        total = sum(w.values()) or 1.0
        w = {k: v / total for k, v in w.items()}
        return w

    def synthesize_scores(
        self,
        factor_values: dict[str, dict[str, float]],
        weights: dict[str, float],
    ) -> dict[str, float]:
        """截面合成：对每只标的按因子权重加权。"""
        scores: dict[str, float] = {}
        for fid, w in weights.items():
            series = factor_values.get(fid, {})
            for symbol, value in series.items():
                scores[symbol] = scores.get(symbol, 0.0) + w * value
        return scores

    @staticmethod
    def estimate_synth_ic_series(
        factor_ic_series: dict[str, Sequence[float]],
        weights: dict[str, float],
    ) -> list[float]:
        """
        用单因子 IC 时序的加权近似估计合成 IC 时序。
        注：忽略因子相关对组合 IC 的二阶影响，适合作为快速验收代理。
        """
        if not weights:
            return []
        length = min(len(v) for v in factor_ic_series.values()) if factor_ic_series else 0
        out: list[float] = []
        for t in range(length):
            val = 0.0
            for fid, w in weights.items():
                series = factor_ic_series.get(fid, [])
                if t < len(series):
                    val += w * series[t]
            out.append(val)
        return out

    def evaluate_synthesis(
        self, synth_ic_series: Sequence[float]
    ) -> dict[str, Any]:
        if not synth_ic_series:
            return {
                "rank_ic_mean": 0.0,
                "icir": 0.0,
                "passed": False,
                "reason": "empty_ic_series",
            }
        mean = sum(synth_ic_series) / len(synth_ic_series)
        if len(synth_ic_series) < 2:
            std = 0.0
        else:
            var = sum((x - mean) ** 2 for x in synth_ic_series) / (
                len(synth_ic_series) - 1
            )
            std = math.sqrt(var)
        icir = mean / std if std > 1e-12 else 0.0
        reasons: list[str] = []
        if abs(mean) < self.config.min_syn_abs_ic:
            reasons.append("syn_ic_below_threshold")
        if abs(icir) < self.config.min_syn_icir:
            reasons.append("syn_icir_below_threshold")
        return {
            "rank_ic_mean": mean,
            "icir": icir,
            "passed": not reasons,
            "reason": ";".join(reasons),
        }

    def run(
        self,
        factor_icir: dict[str, float],
        factor_ic_series: dict[str, Sequence[float]],
        corr_matrix: dict[tuple[str, str], float] | None = None,
        prev_weights: dict[str, float] | None = None,
        factor_values: dict[str, dict[str, float]] | None = None,
        recipe_version: str = "syn-v1",
    ) -> dict[str, Any]:
        weights = self.allocate_weights(factor_icir, corr_matrix, prev_weights)
        approx_ic = self.estimate_synth_ic_series(factor_ic_series, weights)
        metrics = self.evaluate_synthesis(approx_ic)
        scores = (
            self.synthesize_scores(factor_values, weights) if factor_values else {}
        )
        return {
            "recipe_version": recipe_version,
            "config": self.config.to_dict(),
            "weights": weights,
            "metrics": metrics,
            "accepted": metrics["passed"],
            "synthetic_scores": scores,
            "approx_ic_series": approx_ic,
        }
