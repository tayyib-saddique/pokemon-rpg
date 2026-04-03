"""
Health system — shared by Player and Enemy.
"""
from dataclasses import dataclass


@dataclass
class Health:
    max_hp: int
    current: int = None

    def __post_init__(self):
        if self.current is None:
            self.current = self.max_hp

    def take_damage(self, amount: int) -> None:
        self.current = max(0, self.current - amount)

    def heal(self, amount: int) -> None:
        self.current = min(self.max_hp, self.current + amount)

    @property
    def is_dead(self) -> bool:
        return self.current <= 0

    @property
    def ratio(self) -> float:
        """0.0 (empty) to 1.0 (full) — used by the HUD to size the bar."""
        return self.current / self.max_hp if self.max_hp else 0.0
