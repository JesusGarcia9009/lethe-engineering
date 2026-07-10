# Compactor-in-the-Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire the existing `Compactor` into `Session._gc()` so that, under budget pressure, a contiguous run of cold completed blocks is replaced by one dense consolidation note (resident) while the originals are paged out losslessly — making the `COMPACTED` lifecycle state real automatically.

**Architecture:** The `Scheduler` gains a single scoring pass (`score`) plus `cold_run()` to identify the longest compactable run; the `Archivist` gains `compact_out()` (store losslessly, no stub); `Session._gc()` tries compaction before paging and `_try_compact()` swaps the run for a note. Losslessness is preserved because originals are written to the store with handles before removal, and the note carries those handles in `meta["covers"]`.

**Tech Stack:** Python 3.12+ (runtime 3.14), stdlib only, `pytest`. No new dependencies.

## Global Constraints

- **No new dependencies.** Core stays stdlib-only (`pyproject.toml` `dependencies = []`).
- **Full suite must stay green** and `python -m lethe.evals.needle` must still recover the fact under budget.
- **Deterministic scheduler** given scores — no new nondeterminism in policy code.
- **One scoring pass per `_gc` iteration** — `plan()` and `cold_run()` must accept a precomputed `scores=` dict so a real cheap-model curator is never called twice per iteration.
- **Commits attributed to the repo owner:** before the first commit run
  `git config user.email "47598025+JesusGarcia9009@users.noreply.github.com"` and
  `git config user.name "JesusGarcia9009"`. (The repo owner may prefer to run commits himself — if so, hand him the exact commands instead of committing.)
- **Bilingual CHANGELOG** (Keep a Changelog, EN/ES) entry in `[Unreleased]`.

---

### Task 1: Scheduler — single scoring pass + `cold_run`

**Files:**
- Modify: `lethe/core/scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Consumes: `Curator.score(blocks, now_step, goal) -> dict[str, float]` (existing); `Thresholds.cold`, `Thresholds.keep_last_n_steps` (existing).
- Produces:
  - `Scheduler.score(blocks, now_step, goal) -> dict[str, float]`
  - `Scheduler.plan(blocks, now_step, goal, scores: dict | None = None) -> tuple[list[Block], list[Block]]` (adds optional `scores=`)
  - `Scheduler.cold_run(blocks, now_step, goal, scores: dict | None = None) -> list[Block]` — longest contiguous run of compactable blocks, `[]` if none.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_scheduler.py`:

```python
def test_cold_run_selects_leading_cold_contiguous_blocks():
    # now_step=7, span=7: score(step i) = 0.5*(i/7) + 0.1*0.5 (tool_result kind).
    # cold<0.25 holds for i in {0,1,2}; step3+ warmer; steps 6,7 protected.
    blocks = [_b(str(i), i, "x" * 40) for i in range(8)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=2))
    run = sched.cold_run(blocks, now_step=7, goal="g")
    assert [b.id for b in run] == ["0", "1", "2"]


def test_cold_run_excludes_pinned():
    blocks = [_b(str(i), i, "x" * 40) for i in range(6)]
    blocks[1].pinned = True
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=1))
    run = sched.cold_run(blocks, now_step=5, goal="g")
    assert "1" not in {b.id for b in run}


def test_cold_run_empty_when_all_recent_or_protected():
    blocks = [_b(str(i), i, "x" * 40) for i in range(3)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=3))
    run = sched.cold_run(blocks, now_step=2, goal="g")
    assert run == []


def test_plan_accepts_precomputed_scores():
    blocks = [_b(str(i), i, "x" * 40) for i in range(10)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=2))
    scores = sched.score(blocks, now_step=9, goal="g")
    kept, evicted = sched.plan(blocks, now_step=9, goal="g", scores=scores)
    assert sum(FakeTokenCounter().count([b]) for b in kept) <= 50
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: FAIL — `AttributeError: 'Scheduler' object has no attribute 'cold_run'` (and `score`).

- [ ] **Step 3: Implement the Scheduler changes**

Replace the body of `class Scheduler` in `lethe/core/scheduler.py` (keep the imports and `Thresholds` dataclass above it unchanged) with:

```python
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
             scores: dict[str, float] | None = None) -> tuple[list[Block], list[Block]]:
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
                 scores: dict[str, float] | None = None) -> list[Block]:
        """Longest contiguous run of cold, unprotected, compactable blocks (or [])."""
        if scores is None:
            scores = self.score(blocks, now_step, goal)
        protected_steps = self._protected_steps(blocks)

        def compactable(b: Block) -> bool:
            return (not b.pinned
                    and b.created_step not in protected_steps
                    and scores[b.id] < self.th.cold
                    and b.kind != "note"
                    and not b.meta.get("stub_for"))

        best: list[Block] = []
        cur: list[Block] = []
        for b in blocks:
            if compactable(b):
                cur.append(b)
            else:
                if len(cur) > len(best):
                    best = cur
                cur = []
        if len(cur) > len(best):
            best = cur
        return best
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: PASS (all scheduler tests green).

- [ ] **Step 5: Commit**

```bash
git add lethe/core/scheduler.py tests/test_scheduler.py
git commit -m "feat(scheduler): score() + cold_run() with single-pass scores="
```

---

### Task 2: Archivist — `compact_out` (lossless store, no stub)

**Files:**
- Modify: `lethe/agents/archivist.py`
- Test: `tests/test_archivist.py`

**Interfaces:**
- Consumes: `Archivist._fresh_handle()` (existing); `store.put(block)`, `store.get(handle)`, `store.search(query, limit)`, `store.events(kind, payload)` (existing); `BlockState.COMPACTED` (existing).
- Produces: `Archivist.compact_out(block: Block) -> str` — returns the handle; sets `block.state = BlockState.COMPACTED`; leaves no stub.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_archivist.py`:

```python
def test_compact_out_stores_losslessly_without_stub():
    store = MemoryStore()
    arch = Archivist(store)
    b = _b("1", "the launch code is 4242", step=2)
    handle = arch.compact_out(b)
    assert b.state is BlockState.COMPACTED
    assert handle and store.get(handle).content == "the launch code is 4242"
    # recoverable by keyword too
    assert store.search("launch", limit=5)[0].content == "the launch code is 4242"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_archivist.py::test_compact_out_stores_losslessly_without_stub -q`
Expected: FAIL — `AttributeError: 'Archivist' object has no attribute 'compact_out'`.

- [ ] **Step 3: Implement `compact_out`**

In `lethe/agents/archivist.py`, add this method to `class Archivist` immediately after `page_out`:

```python
    def compact_out(self, block: Block) -> str:
        """Store a block that a consolidation note now represents. Lossless, no stub."""
        if block.handle is None:
            block.handle = self._fresh_handle()
        block.state = BlockState.COMPACTED
        self.store.put(block)
        self.store.events("compact_out", {"id": block.id, "handle": block.handle})
        return block.handle
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_archivist.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lethe/agents/archivist.py tests/test_archivist.py
git commit -m "feat(archivist): compact_out — lossless store with no stub, state COMPACTED"
```

---

### Task 3: Session — compaction wired into the GC loop

**Files:**
- Modify: `lethe/core/manager.py`
- Modify: `CHANGELOG.md`
- Test: `tests/test_manager.py`

**Interfaces:**
- Consumes: `Scheduler.score`, `Scheduler.cold_run`, `Scheduler.plan(..., scores=)` (Task 1); `Archivist.compact_out` (Task 2); `Compactor(adapter).compact(run, session) -> Note | None` (existing); `store.put_note(note)` (existing); `BlockState.ACTIVE` (existing).
- Produces: `Session._try_compact(run: list[Block]) -> bool`; `Session.stats()` gains keys `compacted` and `notes`; `Session._evicted` now counts paged **and** compacted blocks.

- [ ] **Step 1: Write the failing integration test**

Append to `tests/test_manager.py`:

```python
def test_compaction_folds_cold_run_into_a_note_losslessly():
    # A summarizing curator so the consolidation note carries real text.
    agent = FakeAdapter(context_window=400, handler=lambda msgs: "SUMMARY of early steps")
    store = MemoryStore()
    cm = ContextManager(agent=agent, curator=agent, store=store,
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="find the code later")
    ctx.add(Block(id="needle", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))
    for i in range(1, 12):
        ctx.add(Block(id=f"n{i}", role="tool", kind="tool_result",
                      content="filler " * 20, created_step=i))
        ctx.render()

    s = ctx.stats()
    # at least one consolidation note was created, covering >= 2 blocks
    assert s["notes"] >= 1 and s["compacted"] >= 2
    # the note persisted with the real summary text
    saved_notes = list(store.notes.values())
    assert saved_notes and "SUMMARY" in saved_notes[0].summary
    # the buried fact is still recoverable losslessly
    got = ctx.recall("launch code")
    assert got is not None and "4242" in got.content
    # budget was respected
    assert s["tokens_with_lethe"] <= cm.scheduler.target_tokens()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_manager.py::test_compaction_folds_cold_run_into_a_note_losslessly -q`
Expected: FAIL — `KeyError: 'notes'` (stats has no `notes` key; compaction not wired).

- [ ] **Step 3: Add imports and Session fields**

In `lethe/core/manager.py`, update the top imports. The current import block is:

```python
from __future__ import annotations

import re

from lethe.core.block import Block, Message, BlockState
from lethe.core.scheduler import Scheduler, Thresholds
from lethe.agents.curator import Curator
from lethe.agents.archivist import Archivist
from lethe.adapters.base import ProviderAdapter
from lethe.stores.memory import MemoryStore
```

Replace it with (adds `uuid` and `Compactor`):

```python
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
```

Then in `Session.__init__`, the current body is:

```python
        self.archivist = Archivist(cm.store)
        self.step = 0
        self._evicted = 0
        self._faults = 0
        # honest baseline: every distinct real block counted once, at full size
        self._seen_tokens: dict[str, int] = {}
```

Replace it with:

```python
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
```

- [ ] **Step 4: Rewrite `_gc` and add `_try_compact`**

In `lethe/core/manager.py`, the current `_gc` method is:

```python
    def _gc(self) -> None:
        target = self.cm.scheduler.target_tokens()
        for _ in range(50):                       # bounded: always terminates
            kept, evicted = self.cm.scheduler.plan(
                self.blocks, now_step=self.step, goal=self.goal)
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
            if self.cm.agent.token_counter.count(self.blocks) <= target:
                break
```

Replace it with (compaction-before-paging, single scoring pass, and the new `_try_compact` helper right after):

```python
    def _gc(self) -> None:
        target = self.cm.scheduler.target_tokens()
        for _ in range(50):                       # bounded: always terminates
            if self.cm.agent.token_counter.count(self.blocks) <= target:
                break
            scores = self.cm.scheduler.score(self.blocks, self.step, self.goal)
            run = self.cm.scheduler.cold_run(
                self.blocks, self.step, self.goal, scores=scores)
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
```

- [ ] **Step 5: Extend `stats()`**

In `lethe/core/manager.py`, the current `stats` method is:

```python
    def stats(self) -> dict:
        return {
            "step": self.step,
            "tokens_with_lethe": self.cm.agent.token_counter.count(self.blocks),
            "tokens_without_lethe": sum(self._seen_tokens.values()),
            "evicted": self._evicted,
            "faults": self._faults,
        }
```

Replace it with:

```python
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
```

- [ ] **Step 6: Run the new test, then the full suite and the needle eval**

Run: `python -m pytest tests/test_manager.py::test_compaction_folds_cold_run_into_a_note_losslessly -q`
Expected: PASS.

Run: `python -m pytest -q`
Expected: PASS — all tests green (the existing `test_manager` and `test_needle` invariants — budget held, needle recovered losslessly — still hold under compaction).

Run: `python -m lethe.evals.needle`
Expected: a dict with `'needle_recovered': True` and `max_tokens_with_lethe <= target_tokens` (200).

- [ ] **Step 7: Update the CHANGELOG**

In `CHANGELOG.md`, under `## [Unreleased]`, add an `### Added / Añadido` bullet (create the heading if the section ordering needs it, matching the existing bilingual style):

```markdown
- **Compactor wired into the GC loop.** Under budget pressure, a contiguous run of cold
  completed blocks is now replaced by one dense consolidation note (resident) while the
  originals are paged out losslessly — the `COMPACTED` lifecycle state now happens
  automatically. `stats()` reports `compacted` and `notes`. / **Compactor conectado al loop:**
  bajo presión de presupuesto, un run contiguo de bloques fríos se reemplaza por una nota
  densa residente y los originales se paginan sin pérdida — el estado `COMPACTED` ya ocurre
  automáticamente. `stats()` reporta `compacted` y `notes`.
```

- [ ] **Step 8: Commit**

```bash
git add lethe/core/manager.py tests/test_manager.py CHANGELOG.md
git commit -m "feat(manager): wire Compactor into _gc — cold runs become resident notes

Fixes review finding C2: COMPACTED is now a real automatic state. Compaction
fires only under budget pressure, before paging; originals stored losslessly
with provenance handles in the note's meta['covers']."
```

---

## Notes for the executor

- **Repo owner commits himself.** If so, run the tests for each task and hand him the exact
  `git add` / `git commit` commands above instead of committing.
- **Do not touch** `lethe/mcp/` — the MCP path stays manual archive/recall this release.
- After Task 3, an optional release bump to `v0.7.0` in `pyproject.toml` + tag is a separate
  decision for the owner, not part of this plan.
