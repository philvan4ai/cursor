from __future__ import annotations

from typing import Any, Sequence

from framework.common.models import RiskAction, RiskEvent, RiskLevel
from framework.nav_risk.config import NavRiskConfig
from framework.nav_risk.metrics import compute_nav_metrics


class NavRiskManager:
    """
    净值风控管理：
    计算指标 → 分级判定 → 生成处置动作与审计事件。
    """

    def __init__(self, config: NavRiskConfig | None = None) -> None:
        self.config = config or NavRiskConfig()
        self.events: list[RiskEvent] = []

    def evaluate_snapshot(
        self,
        date: str,
        drawdown: float,
        rolling_vol: float,
    ) -> RiskEvent | None:
        cfg = self.config

        if drawdown >= cfg.offline_drawdown:
            event = RiskEvent(
                date=date,
                level=RiskLevel.L4_OFFLINE,
                action=RiskAction.LIQUIDATE_OR_SWITCH,
                reason="drawdown_offline_threshold",
                metrics={"drawdown": drawdown, "rolling_vol": rolling_vol},
                scale=0.0,
            )
        elif drawdown >= cfg.freeze_drawdown:
            event = RiskEvent(
                date=date,
                level=RiskLevel.L3_FREEZE,
                action=RiskAction.FREEZE_OPEN,
                reason="drawdown_freeze_threshold",
                metrics={"drawdown": drawdown, "rolling_vol": rolling_vol},
                scale=1.0,
            )
        elif drawdown >= cfg.hard_drawdown or rolling_vol >= cfg.hard_vol:
            event = RiskEvent(
                date=date,
                level=RiskLevel.L2_DELEVERAGE,
                action=RiskAction.REDUCE_EXPOSURE,
                reason="hard_risk_threshold",
                metrics={"drawdown": drawdown, "rolling_vol": rolling_vol},
                scale=cfg.deleverage_scale,
            )
        elif drawdown >= cfg.soft_drawdown or rolling_vol >= cfg.soft_vol:
            event = RiskEvent(
                date=date,
                level=RiskLevel.L1_ALERT,
                action=RiskAction.ALERT,
                reason="soft_risk_threshold",
                metrics={"drawdown": drawdown, "rolling_vol": rolling_vol},
                scale=1.0,
            )
        else:
            return None

        self.events.append(event)
        return event

    def apply_to_exposure(self, current_exposure: float, event: RiskEvent | None) -> float:
        """按风控事件缩放组合敞口。"""
        if event is None:
            return current_exposure
        if event.level == RiskLevel.L4_OFFLINE:
            return 0.0
        if event.level in {RiskLevel.L2_DELEVERAGE, RiskLevel.L3_FREEZE}:
            # L2/L3：至少执行一次风险预算收缩；L3 另含停止开仓语义
            scale = event.scale if event.level == RiskLevel.L2_DELEVERAGE else min(
                event.scale, self.config.deleverage_scale
            )
            return current_exposure * scale
        return current_exposure

    @staticmethod
    def _severity(level: RiskLevel) -> int:
        order = {
            RiskLevel.L1_ALERT: 1,
            RiskLevel.L2_DELEVERAGE: 2,
            RiskLevel.L3_FREEZE: 3,
            RiskLevel.L4_OFFLINE: 4,
        }
        return order[level]

    def run(
        self,
        dates: Sequence[str],
        navs: Sequence[float],
        current_exposure: float = 1.0,
    ) -> dict[str, Any]:
        snapshots = compute_nav_metrics(
            dates, navs, rolling_window=self.config.rolling_window
        )
        latest_event: RiskEvent | None = None
        peak_event: RiskEvent | None = None
        for snap in snapshots:
            event = self.evaluate_snapshot(
                snap.date, snap.drawdown, snap.rolling_vol
            )
            if event is None:
                continue
            latest_event = event
            if peak_event is None or self._severity(event.level) > self._severity(
                peak_event.level
            ):
                peak_event = event

        # 敞口按期间内最高风险级别处置（L3 冻结开仓不被动降仓）
        new_exposure = self.apply_to_exposure(current_exposure, peak_event)
        latest = snapshots[-1] if snapshots else None

        return {
            "config": self.config.to_dict(),
            "latest_nav": None
            if latest is None
            else {
                "date": latest.date,
                "nav": latest.nav,
                "drawdown": latest.drawdown,
                "rolling_vol": latest.rolling_vol,
                "rolling_sharpe": latest.rolling_sharpe,
            },
            "latest_event": None if latest_event is None else latest_event.to_dict(),
            "peak_event": None if peak_event is None else peak_event.to_dict(),
            "exposure_before": current_exposure,
            "exposure_after": new_exposure,
            "events": [e.to_dict() for e in self.events],
            "snapshots": [
                {
                    "date": s.date,
                    "nav": s.nav,
                    "daily_return": s.daily_return,
                    "drawdown": s.drawdown,
                    "rolling_vol": s.rolling_vol,
                    "rolling_sharpe": s.rolling_sharpe,
                }
                for s in snapshots
            ],
        }
