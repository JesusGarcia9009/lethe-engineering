from __future__ import annotations

import re
import uuid

from lethe.core.block import Block, Message, BlockState
from lethe.core.scheduler import Scheduler, Thresholds
from lethe.agents.curator import Curator
from lethe.agents.archivist import Archivist
from lethe.agents.compactor import Compactor
from lethe.adapters.base import ProviderAdapter
from lethe.stores.memory import MemoryStore

_HANDLE_RE = re.compile(r"handle=([0-9a-f]{4,})")


def _is_stub(b: Block) -> bool:
    return bool(b.meta.get("stub_for"))


class Session:
    def __init__(self, cm: "ContextManager", goal: str, subgoal: str | None):
        self.cm = cm
        self.goal = goal
        self.subgoal = subgoal
        self.blocks: list[Block] = []
        self.archivist = Archivist(cm.store)
        self.compactor = Compactor(cm.curator_adapter)
        self.session_id = uuid.uuid4().hex[:8]
        self.step = 0
        self._evicted = 0
        self._compacted = 0
        self._notes = 0
        self._faults = 0
        # honest baseline: every distinct real block counted once, at full size
        self._seen_tokens: dict[str, int] = {}

    def set_subgoal(self, subgoal: str | None) -> None:
        """Advance the active subgoal. Blocks of the previous subgoal become
        eligible for compaction; blocks added now are tagged with the new one."""
        self.subgoal = subgoal

    def add(self, block: Block) -> None:
        if block.tokens is None:
            block.tokens = self.cm.agent.token_counter.count([block])
        if self.subgoal is not None:
            block.meta.setdefault("subgoal", self.subgoal)
        self._seen_tokens[block.id] = block.tokens
        self.blocks.append(block)
        self.step = max(self.step, block.created_step)
        if self.cm.should_trigger(self.step):
            self._gc()

    def _gc(self) -> None:
        target = self.cm.scheduler.target_tokens()
        for _ in range(50):                       # bounded: always terminates
            if self.cm.agent.token_counter.count(self.blocks) <= target:
                break
            scores = self.cm.scheduler.score(self.blocks, self.step, self.goal)
            run = self.cm.scheduler.cold_run(
                self.blocks, self.step, self.goal, scores=scores,
                open_subgoal=self.subgoal)
            if len(run) >= 2 and self._try_compact(run):
                continue                          # recount at top of loop
            kept, evicted = self.cm.scheduler.plan(
                self.blocks, now_step=self.step, goal=self.goal, scores=scores)
            if not evicted:
                break
            new_blocks = list(kept)
            for b in evicted:
                if _is_stub(b):
                    # content already safe in the store; just drop the stale stub
                    self.cm.store.events("stub_drop", {"handle": b.handle})
                    continue
                stub = self.archivist.page_out(b)
                new_blocks.append(stub)
                self._evicted += 1
            self.blocks = new_blocks

    def _try_compact(self, run: list[Block]) -> bool:
        """Fold a cold run into one resident note; page the originals out losslessly."""
        note = self.compactor.compact(run, session=self.session_id)
        if note is None:
            return False
        handles = [self.archivist.compact_out(b) for b in run]
        note_block = Block(
            id=f"note-{note.id}", role="assistant", kind="note",
            content=note.summary, created_step=run[-1].created_step,
            state=BlockState.ACTIVE, tokens=note.tokens,
            meta={"covers": handles, "note_id": note.id},
        )
        self.cm.store.put_note(note)
        run_ids = {b.id for b in run}
        new_blocks: list[Block] = []
        inserted = False
        for b in self.blocks:
            if b.id in run_ids:
                if not inserted:
                    new_blocks.append(note_block)
                    inserted = True
                self._evicted += 1
                self._compacted += 1
            else:
                new_blocks.append(b)
        self.blocks = new_blocks
        self._notes += 1
        return True

    def render(self) -> list[Message]:
        self._gc()
        return [Message(role=b.role, blocks=[b]) for b in self.blocks]

    def observe(self, response) -> None:
        """Record handles the model referenced and page those blocks back in."""
        for h in set(_HANDLE_RE.findall(response.text)):
            block = self.archivist.page_fault(h)
            if block and not any(b.id == block.id for b in self.blocks):
                self.blocks.append(block)
                self._faults += 1
                # drop the now-redundant stub for this block
                self.blocks = [b for b in self.blocks
                               if b.meta.get("stub_for") != block.id]

    def recall(self, query_or_handle: str) -> Block | None:
        if re.fullmatch(r"[0-9a-f]{4,}", query_or_handle):
            block = self.archivist.page_fault(query_or_handle)
            if block:
                return block
        hits = self.archivist.recall(query_or_handle)
        return hits[0] if hits else None

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
            "tokens_without_lethe": sum(self._seen_tokens.values()),
            "evicted": self._evicted,
            "compacted": self._compacted,
            "notes": self._notes,
            "faults": self._faults,
        }


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
