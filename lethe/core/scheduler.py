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

    def score(self, blocks: list[Block], now_step: int, goal: str) -> dict[str, float]:
        return self.curator.score(blocks, now_step=now_step, goal=goal)

    def _protected_steps(self, blocks: list[Block]) -> set[int]:
        return set(sorted({b.created_step for b in blocks})[-self.th.keep_last_n_steps:])

    def plan(self, blocks: list[Block], now_step: int, goal: str,
             scores: dict[str, float] | None = None
             ) -> tuple[list[Block], list[Block]]:
        """Return (kept, evicted). Deterministic given scores."""
        if scores is None:
            scores = self.score(blocks, now_step, goal)
        protected_steps = self._protected_steps(blocks)

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

    def cold_run(self, blocks: list[Block], now_step: int, goal: str,
                 scores: dict[str, float] | None = None,
                 open_subgoal: str | None = None) -> list[Block]:
        """Longest contiguous run of cold, unprotected, compactable blocks (or []).

        Never compacts blocks of the still-open subgoal, and never lets a run span
        a subgoal boundary (never_compact_open_subgoal safety guarantee).
        """
        if scores is None:
            scores = self.score(blocks, now_step, goal)
        protected_steps = self._protected_steps(blocks)

        def compactable(b: Block) -> bool:
            return (not b.pinned
                    and b.created_step not in protected_steps
                    and scores[b.id] < self.th.cold
                    and b.kind != "note"
                    and not b.meta.get("stub_for")
                    and not (open_subgoal is not None
                             and b.meta.get("subgoal") == open_subgoal))

        best: list[Block] = []
        cur: list[Block] = []
        for b in blocks:
            if not compactable(b):
                if len(cur) > len(best):
                    best = cur
                cur = []
                continue
            if cur and b.meta.get("subgoal") != cur[0].meta.get("subgoal"):
                # subgoal boundary: close the current run, start a fresh one
                if len(cur) > len(best):
                    best = cur
                cur = []
            cur.append(b)
        if len(cur) > len(best):
            best = cur
        return best
