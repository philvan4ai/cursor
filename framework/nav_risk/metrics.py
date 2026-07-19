from __future__ import annotations

import math
from typing import Sequence

from framework.common.models import NavSnapshot


def _mean(xs: Sequence[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _std(xs: Sequence[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    var = sum((x - m) ** 2 for x in xs) / (len(xs) - 1)
    return math.sqrt(var)


def compute_nav_metrics(
    dates: Sequence[str],
    navs: Sequence[float],
    rolling_window: int = 20,
) -> list[NavSnapshot]:
    """由净值序列计算日收益、回撤、滚动波动与滚动夏普。"""
    if len(dates) != len(navs):
        raise ValueError("dates and navs length mismatch")
    if not navs:
        return []

    peak = navs[0]
    snapshots: list[NavSnapshot] = []
    rets: list[float] = []

    for i, (date, nav) in enumerate(zip(dates, navs)):
        if i == 0:
            daily_ret = 0.0
        else:
            prev = navs[i - 1]
            daily_ret = (nav / prev - 1.0) if prev > 0 else 0.0
        rets.append(daily_ret)
        peak = max(peak, nav)
        drawdown = 1.0 - nav / peak if peak > 0 else 0.0

        window = rets[max(0, i + 1 - rolling_window) : i + 1]
        vol = _std(window) * math.sqrt(252)
        mu = _mean(window) * 252
        sharpe = mu / vol if vol > 1e-12 else 0.0

        snapshots.append(
            NavSnapshot(
                date=date,
                nav=nav,
                daily_return=daily_ret,
                drawdown=drawdown,
                rolling_vol=vol,
                rolling_sharpe=sharpe,
            )
        )
    return snapshots
