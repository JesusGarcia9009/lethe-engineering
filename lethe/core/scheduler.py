from __future__ import annotations

from dataclasses import dataclass

from lethe.core.block import Block
from lethe.agents.curator import Curator
from lethe.adapters.base import TokenCounter


@dataclass
class Thresholds:
    warm: float = 0.45
    cold: float = 0.25
    fault_in: float = 0.7
    keep_last_n_steps: int = 3


class Scheduler:
    def __init__(self, curator: Curator, token_counter: TokenCounter,
                 budget: float, context_window: int, thresholds: Thresholds | None = None):
        self.curator = curator
        self.tc = token_counter
        self.budget = budget
        self.context_window = context_window
        self.th = thresholds or Thresholds()

    def target_tokens(self) -> int:
        return int(self.context_window * self.budget)

    def plan(self, blocks: list[Block], now_step: int, goal: str
             ) -> tuple[list[Block], list[Block]]:
        """Return (kept, evicted). Deterministic given scores."""
        scores = self.curator.score(blocks, now_step=now_step, goal=goal)
        protected_steps = set(
            sorted({b.created_step for b in blocks})[-self.th.keep_last_n_steps:]
        )

        def protected(b: Block) -> bool:
            return b.pinned or b.created_step in protected_steps

        kept = list(blocks)
        target = self.target_tokens()
        evictable = sorted(
            (b for b in blocks if not protected(b)),
            key=lambda b: scores[b.id],
        )
        evicted: list[Block] = []
        idx = 0
        while self.tc.count(kept) > target and idx < len(evictable):
            victim = evictable[idx]
            idx += 1
            kept.remove(victim)
            evicted.append(victim)
        return kept, evicted
