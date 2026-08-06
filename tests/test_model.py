"""核心动力学与定性回归测试。"""

from __future__ import annotations

import numpy as np

from src.model import BatteryPolicyGame, GameParams
from src.scenarios import SCENARIOS, run_scenario


def _at(tr, year: float, field: str = "q_real") -> float:
    idx = int(np.argmin(np.abs(2023.0 + tr.t - year)))
    return float(getattr(tr, field)[idx])


def test_payoff_shapes():
    g = BatteryPolicyGame()
    pr, po = g.payoffs_policy(0.4, 0.5, 4.0)
    pf, pg = g.payoffs_industry(0.4, 0.5, 4.0)
    assert np.isfinite(pr) and np.isfinite(po)
    assert np.isfinite(pf) and np.isfinite(pg)


def test_replicator_bounded():
    g = BatteryPolicyGame()
    tr = g.simulate(0.3, 0.3, t_span=(0, 5), n_steps=200)
    assert np.all(tr.r >= 0) and np.all(tr.r <= 1)
    assert np.all(tr.f >= 0) and np.all(tr.f <= 1)
    assert np.all(tr.q_real > 0)
    assert np.all(tr.eta > 0) and np.all(tr.eta <= 1)


def test_climate_targets_ordered():
    steps = run_scenario(SCENARIOS["race_steps"])
    aps = run_scenario(SCENARIOS["race_aps"])
    nze = run_scenario(SCENARIOS["race_nze"])
    assert _at(steps, 2030, "q_star") < _at(aps, 2030, "q_star") < _at(nze, 2030, "q_star")


def test_restriction_reduces_installation_under_nze():
    open_ = run_scenario(SCENARIOS["open_nze"])
    race = run_scenario(SCENARIOS["race_nze"])
    assert _at(race, 2030, "q_real") < _at(open_, 2030, "q_real") * 0.85
    assert _at(race, 2030, "gap") > _at(open_, 2030, "gap")


def test_coop_beats_race_on_nze_gap():
    coop = run_scenario(SCENARIOS["coop_climate"])
    race = run_scenario(SCENARIOS["race_nze"])
    assert _at(coop, 2030, "gap") < _at(race, 2030, "gap")
    assert _at(coop, 2030, "r") < _at(race, 2030, "r")


def test_mineral_hard_hurts_efficiency():
    mild = run_scenario(SCENARIOS["mild_ira"])
    hard = run_scenario(SCENARIOS["mineral_hard"])
    assert _at(hard, 2030, "eta") < _at(mild, 2030, "eta")


def test_nze_alpha_higher_than_steps():
    assert GameParams(climate="NZE").climate_alpha > GameParams(climate="STEPS").climate_alpha
