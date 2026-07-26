"""核心动力学与校准回归测试。"""

from __future__ import annotations

import numpy as np

from src.model import EvolutionaryChipGame, GameParams
from src.scenarios import SCENARIOS, run_scenario


def _share_at(tr, year: float) -> float:
    idx = int(np.argmin(np.abs(2021.0 + tr.t - year)))
    return float(tr.x[idx])


def test_payoff_shapes():
    g = EvolutionaryChipGame()
    pd, pn = g.payoffs_adopters(0.4, 0.5, 0.8, 4.0)
    ph, pl = g.payoffs_suppliers(0.4, 0.5, 0.8, 4.0)
    assert np.isfinite(pd) and np.isfinite(pn)
    assert np.isfinite(ph) and np.isfinite(pl)


def test_replicator_bounded():
    g = EvolutionaryChipGame()
    tr = g.simulate(0.1, 0.2, t_span=(0, 5), n_steps=200, sigma_path=0.7)
    assert np.all(tr.x >= 0) and np.all(tr.x <= 1)
    assert np.all(tr.y >= 0) and np.all(tr.y <= 1)


def test_wsj_calibration_corridor():
    tr = run_scenario(SCENARIOS["wsj_dilemma"])
    s2025 = _share_at(tr, 2025)
    s2030 = _share_at(tr, 2030)
    assert 0.30 <= s2025 <= 0.55, s2025
    assert 0.65 <= s2030 <= 0.88, s2030


def test_hard_ban_beats_sell_soft():
    hard = run_scenario(SCENARIOS["hard_ban"])
    soft = run_scenario(SCENARIOS["sell_soft"])
    assert _share_at(hard, 2030) > _share_at(soft, 2030) + 0.15


def test_euv_raises_ceiling():
    base = EvolutionaryChipGame(GameParams(euv_breakthrough=False))
    euv = EvolutionaryChipGame(GameParams(euv_breakthrough=True))
    assert euv.kappa(8.0) > base.kappa(8.0)


def test_wall_corner_helps_high_effort():
    g = EvolutionaryChipGame()
    d_low = g.payoffs_suppliers(0.3, 0.4, 0.2, 3.0)
    d_high = g.payoffs_suppliers(0.3, 0.4, 0.9, 3.0)
    assert (d_high[0] - d_high[1]) > (d_low[0] - d_low[1])
