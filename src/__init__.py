"""国产芯片 vs 英伟达：演化博弈分析包。"""

from .model import EvolutionaryChipGame, GameParams
from .scenarios import SCENARIOS, run_all_scenarios

__all__ = [
    "EvolutionaryChipGame",
    "GameParams",
    "SCENARIOS",
    "run_all_scenarios",
]
