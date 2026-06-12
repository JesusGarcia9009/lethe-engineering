from __future__ import annotations

from lethe.core.block import Block, Message, BlockState
from lethe.core.scheduler import Scheduler, Thresholds
from lethe.agents.curator import Curator
from lethe.adapters.base import ProviderAdapter
from lethe.stores.memory import MemoryStore


class Session:
    def __init__(self, cm: "ContextManager", goal: str, subgoal: str | None):
        self.cm = cm
        self.goal = goal
        self.subgoal = subgoal
        self.blocks: list[Block] = []
        self.step = 0
        self._evicted = 0
        self._faults = 0

    def add(self, block: Block) -> None:
        if block.tokens is None:
            block.tokens = self.cm.agent.token_counter.count([block])
        self.blocks.append(block)
        self.step = max(self.step, block.created_step)
        if self.cm.should_trigger(self.step):
            self._gc()

    def _gc(self) -> None:
        kept, evicted = self.cm.scheduler.plan(
            self.blocks, now_step=self.step, goal=self.goal)
        for b in evicted:
            b.state = BlockState.PAGED
            self.cm.store.put(b)
            self.cm.store.events("page_out", {"id": b.id})
        self._evicted += len(evicted)
        self.blocks = kept

    def render(self) -> list[Message]:
        self._gc()
        return [Message(role=b.role, blocks=[b]) for b in self.blocks]

    def pin(self, block_id: str) -> None:
        for b in self.blocks:
            if b.id == block_id:
                b.pinned = True

    def unpin(self, block_id: str) -> None:
        for b in self.blocks:
            if b.id == block_id:
                b.pinned = False

    def stats(self) -> dict:
        return {
            "step": self.step,
            "tokens_with_lethe": self.cm.agent.token_counter.count(self.blocks),
            "tokens_without_lethe": self._tokens_without(),
            "evicted": self._evicted,
            "faults": self._faults,
        }

    def _tokens_without(self) -> int:
        # every block ever added: resident working set + everything paged to the store
        resident = self.cm.agent.token_counter.count(self.blocks)
        paged = sum(b.tokens or 0 for b in self.cm.store._by_id.values())
        return resident + paged


class ContextManager:
    def __init__(self, agent: ProviderAdapter, curator: ProviderAdapter | None = None,
                 store=None, budget: float = 0.6, triggers: dict | None = None,
                 thresholds: Thresholds | None = None):
        self.agent = agent
        self.curator_adapter = curator or agent
        self.store = store or MemoryStore()
        self.budget = budget
        self.triggers = triggers or {"every_steps": 5, "on_budget": True}
        self.scheduler = Scheduler(
            Curator(adapter=self.curator_adapter), agent.token_counter, budget=budget,
            context_window=agent.context_window, thresholds=thresholds,
        )

    def session(self, goal: str, subgoal: str | None = None) -> Session:
        return Session(self, goal, subgoal)

    def should_trigger(self, step: int) -> bool:
        every = self.triggers.get("every_steps")
        return bool(every) and step > 0 and step % every == 0
