# LETHE Vertical Slice — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a single-provider (Claude) end-to-end context garbage collector that scores, compacts, and pages LLM context blocks losslessly, proven by a needle-in-haystack test and a live terminal visualizer.

**Architecture:** Pure provider-agnostic types at the core; a `FakeAdapter` enables deterministic TDD with no network; agents (Curator, Compactor, Archivist) depend only on abstract `ProviderAdapter`/`Store` interfaces; a `Scheduler` orchestrates score→decide→compact→page on triggers; a `ContextManager` is the public API. Retrieval is handle + lexical (SQLite FTS5), no embeddings.

**Tech Stack:** Python 3.14, stdlib `sqlite3` (FTS5), `anthropic` SDK (real adapter only), `pytest`.

---

## File structure

```
lethe/
  __init__.py        # exports ContextManager, wrap (later), Block
  core/
    __init__.py
    block.py         # Block, Message, BlockState
    manager.py       # ContextManager
    scheduler.py     # Scheduler
  adapters/
    __init__.py
    base.py          # ProviderAdapter, Response, TokenCounter
    fake.py          # FakeAdapter (+ FakeTokenCounter)
    anthropic.py     # AnthropicAdapter
  agents/
    __init__.py
    curator.py       # Curator
    compactor.py     # Compactor
    archivist.py     # Archivist
  stores/
    __init__.py
    base.py          # Store protocol, Note
    memory.py        # MemoryStore
    sqlite.py        # SqliteStore (FTS5)
  viz/
    __init__.py
    console.py       # render_frame
  evals/
    needle.py        # needle test driver
  examples/
    claude_loop.py   # real Claude loop
tests/
  test_block.py  test_fake.py  test_memory_store.py
  test_curator.py  test_scheduler.py  test_manager.py
  test_compactor.py  test_sqlite_store.py  test_archivist.py
  test_needle.py  test_viz.py
pyproject.toml
README.md
```

Each milestone below leaves a green test suite.

---

## Milestone A — Foundation (Phase 0)

### Task 1: Project scaffold

**Files:**
- Create: `pyproject.toml`
- Create: `lethe/__init__.py`, `lethe/core/__init__.py`, `lethe/adapters/__init__.py`, `lethe/agents/__init__.py`, `lethe/stores/__init__.py`, `lethe/viz/__init__.py`, `lethe/evals/__init__.py`, `lethe/examples/__init__.py`
- Create: `tests/__init__.py`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
[project]
name = "lethe"
version = "0.1.0"
description = "Live Ephemeral Token & History Engine — context GC for LLM agents"
requires-python = ">=3.12"
dependencies = []

[project.optional-dependencies]
anthropic = ["anthropic>=0.40"]
dev = ["pytest>=8"]

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Create empty `__init__.py` files**

Create each `__init__.py` listed above as an empty file (0 bytes). `lethe/__init__.py` may contain a comment `# LETHE package`.

- [ ] **Step 3: Verify pytest runs (no tests yet)**

Run: `python -m pytest -q`
Expected: `no tests ran` (exit cleanly, no import errors).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml lethe tests
git commit -m "chore: scaffold lethe package"
```

---

### Task 2: Core types (`block.py`)

**Files:**
- Create: `lethe/core/block.py`
- Test: `tests/test_block.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_block.py
from lethe.core.block import Block, Message, BlockState

def test_block_defaults():
    b = Block(id="1", role="tool", kind="tool_result", content="hi", created_step=0)
    assert b.state is BlockState.ACTIVE
    assert b.pinned is False
    assert b.tokens is None
    assert b.refs == []
    assert b.handle is None

def test_message_holds_blocks():
    b = Block(id="1", role="user", kind="text", content="hello", created_step=0)
    m = Message(role="user", blocks=[b])
    assert m.blocks[0].content == "hello"

def test_blockstate_values():
    assert {s.value for s in BlockState} == {
        "active", "warm", "compacted", "paged", "rehydrated"
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_block.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.core.block'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/core/block.py
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

class BlockState(Enum):
    ACTIVE = "active"
    WARM = "warm"
    COMPACTED = "compacted"
    PAGED = "paged"
    REHYDRATED = "rehydrated"

Role = Literal["system", "user", "assistant", "tool", "reasoning"]
Kind = Literal["text", "tool_call", "tool_result", "file", "image", "note"]

@dataclass
class Block:
    id: str
    role: Role
    kind: Kind
    content: str
    created_step: int
    pinned: bool = False
    state: BlockState = BlockState.ACTIVE
    tokens: int | None = None
    handle: str | None = None
    refs: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

@dataclass
class Message:
    role: str
    blocks: list[Block] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_block.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/core/block.py tests/test_block.py
git commit -m "feat: core block and message types"
```

---

### Task 3: Adapter base (`adapters/base.py`)

**Files:**
- Create: `lethe/adapters/base.py`

- [ ] **Step 1: Write minimal implementation (interfaces only — exercised by Task 4 tests)**

```python
# lethe/adapters/base.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from lethe.core.block import Block, Message

@runtime_checkable
class TokenCounter(Protocol):
    def count(self, blocks: list[Block]) -> int: ...

@dataclass
class Response:
    text: str
    raw: Any = None

@runtime_checkable
class ProviderAdapter(Protocol):
    name: str
    context_window: int
    token_counter: TokenCounter
    def complete(self, messages: list[Message], **kw: Any) -> Response: ...
```

- [ ] **Step 2: Verify it imports**

Run: `python -c "import lethe.adapters.base"`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add lethe/adapters/base.py
git commit -m "feat: provider adapter, token counter, response interfaces"
```

---

### Task 4: FakeAdapter (`adapters/fake.py`)

**Files:**
- Create: `lethe/adapters/fake.py`
- Test: `tests/test_fake.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_fake.py
from lethe.core.block import Block, Message
from lethe.adapters.fake import FakeAdapter, FakeTokenCounter

def _b(content, **kw):
    kw.setdefault("role", "tool"); kw.setdefault("kind", "tool_result")
    kw.setdefault("created_step", 0)
    return Block(id=kw.pop("id", "x"), content=content, **kw)

def test_token_counter_is_deterministic():
    tc = FakeTokenCounter()
    blocks = [_b("abcd"), _b("abcdefgh")]   # 4 and 8 chars -> 1 and 2 tokens
    assert tc.count(blocks) == 3
    assert tc.count(blocks) == 3            # stable

def test_complete_returns_scripted_response():
    a = FakeAdapter(scripted=["RESULT-1", "RESULT-2"])
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "RESULT-1"
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "RESULT-2"

def test_complete_uses_handler_when_given():
    # handler receives messages, returns text — lets curator tests drive scores
    a = FakeAdapter(handler=lambda msgs: "0.9")
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "0.9"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_fake.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.adapters.fake'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/adapters/fake.py
from __future__ import annotations
from math import ceil
from typing import Callable
from lethe.core.block import Block, Message
from lethe.adapters.base import Response

class FakeTokenCounter:
    """Deterministic: ~1 token per 4 characters of content."""
    def count(self, blocks: list[Block]) -> int:
        return sum(max(1, ceil(len(b.content) / 4)) for b in blocks)

class FakeAdapter:
    name = "fake"

    def __init__(self, scripted: list[str] | None = None,
                 handler: Callable[[list[Message]], str] | None = None,
                 context_window: int = 1000):
        self.context_window = context_window
        self.token_counter = FakeTokenCounter()
        self._scripted = list(scripted or [])
        self._handler = handler
        self._i = 0

    def complete(self, messages: list[Message], **kw) -> Response:
        if self._handler is not None:
            return Response(text=self._handler(messages))
        if self._i < len(self._scripted):
            text = self._scripted[self._i]; self._i += 1
            return Response(text=text)
        return Response(text="")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_fake.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/adapters/fake.py tests/test_fake.py
git commit -m "feat: deterministic FakeAdapter and token counter for TDD"
```

---

### Task 5: Store interface + MemoryStore

**Files:**
- Create: `lethe/stores/base.py`
- Create: `lethe/stores/memory.py`
- Test: `tests/test_memory_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_memory_store.py
from lethe.core.block import Block
from lethe.stores.memory import MemoryStore

def _b(id, content, handle=None):
    return Block(id=id, role="tool", kind="tool_result", content=content,
                 created_step=0, handle=handle)

def test_put_and_get_by_handle():
    s = MemoryStore()
    s.put(_b("1", "config contents", handle="a3f9"))
    got = s.get("a3f9")
    assert got is not None and got.content == "config contents"

def test_lexical_search_finds_keyword():
    s = MemoryStore()
    s.put(_b("1", "the secret needle is 4242", handle="h1"))
    s.put(_b("2", "unrelated log line", handle="h2"))
    hits = s.search("needle", limit=5)
    assert [h.id for h in hits] == ["1"]

def test_events_are_recorded():
    s = MemoryStore()
    s.events("page_out", {"handle": "h1"})
    assert s.event_log[-1]["kind"] == "page_out"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_memory_store.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.stores.memory'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/stores/base.py
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from lethe.core.block import Block

@dataclass
class Note:
    id: str
    session: str
    summary: str
    covers: list[str] = field(default_factory=list)   # block ids it replaces
    tokens: int | None = None

class Store(Protocol):
    def put(self, block: Block) -> None: ...
    def get(self, handle: str) -> Block | None: ...
    def search(self, query: str, limit: int) -> list[Block]: ...
    def put_note(self, note: Note) -> None: ...
    def events(self, kind: str, payload: dict) -> None: ...
```

```python
# lethe/stores/memory.py
from __future__ import annotations
from lethe.core.block import Block
from lethe.stores.base import Note

class MemoryStore:
    def __init__(self):
        self._by_handle: dict[str, Block] = {}
        self._by_id: dict[str, Block] = {}
        self.notes: dict[str, Note] = {}
        self.event_log: list[dict] = []

    def put(self, block: Block) -> None:
        self._by_id[block.id] = block
        if block.handle:
            self._by_handle[block.handle] = block

    def get(self, handle: str) -> Block | None:
        return self._by_handle.get(handle)

    def search(self, query: str, limit: int) -> list[Block]:
        q = query.lower()
        hits = [b for b in self._by_id.values() if q in b.content.lower()]
        hits.sort(key=lambda b: b.created_step)
        return hits[:limit]

    def put_note(self, note: Note) -> None:
        self.notes[note.id] = note

    def events(self, kind: str, payload: dict) -> None:
        self.event_log.append({"kind": kind, "payload": payload})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_memory_store.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/stores/base.py lethe/stores/memory.py tests/test_memory_store.py
git commit -m "feat: store interface and in-memory store with lexical search"
```

**Milestone A complete:** foundation types, fake adapter, memory store — all green.

---

## Milestone B — Heuristic engine (Phase 1)

### Task 6: Curator heuristics

**Files:**
- Create: `lethe/agents/curator.py`
- Test: `tests/test_curator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_curator.py
from lethe.core.block import Block
from lethe.agents.curator import Curator

def _b(id, step, content="x", kind="tool_result", pinned=False, refs=None):
    return Block(id=id, role="tool", kind=kind, content=content,
                 created_step=step, pinned=pinned, refs=refs or [])

def test_pinned_block_scores_one():
    c = Curator()
    b = _b("p", 0, pinned=True)
    assert c.score([b], now_step=10, goal="anything")[b.id] == 1.0

def test_recent_block_scores_higher_than_old():
    c = Curator()
    old = _b("old", 0); new = _b("new", 9)
    s = c.score([old, new], now_step=10, goal="g")
    assert s["new"] > s["old"]

def test_referenced_block_gets_keep_boost():
    c = Curator()
    cited = _b("cited", 0)
    citer = _b("citer", 1, refs=["cited"])
    s = c.score([cited, citer], now_step=10, goal="g")
    # same recency baseline but 'cited' is referenced -> higher
    assert s["cited"] > c.score([_b("cited", 0)], now_step=10, goal="g")["cited"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_curator.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.agents.curator'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/agents/curator.py
from __future__ import annotations
from lethe.core.block import Block

KIND_WEIGHT = {
    "note": 1.0, "text": 0.7, "file": 0.6, "tool_call": 0.6,
    "tool_result": 0.5, "image": 0.4,
}

class Curator:
    """Heuristic relevance scoring. Model judgment added in a later task."""

    def __init__(self, w_recency: float = 0.6, w_refs: float = 0.3, w_kind: float = 0.1):
        self.w_recency = w_recency
        self.w_refs = w_refs
        self.w_kind = w_kind

    def score(self, blocks: list[Block], now_step: int, goal: str) -> dict[str, float]:
        ref_counts: dict[str, int] = {}
        for b in blocks:
            for r in b.refs:
                ref_counts[r] = ref_counts.get(r, 0) + 1
        span = max(now_step, 1)
        out: dict[str, float] = {}
        for b in blocks:
            if b.pinned:
                out[b.id] = 1.0
                continue
            recency = max(0.0, 1.0 - (now_step - b.created_step) / span)
            refs = min(1.0, ref_counts.get(b.id, 0) / 2.0)
            kind = KIND_WEIGHT.get(b.kind, 0.5)
            out[b.id] = round(
                self.w_recency * recency + self.w_refs * refs + self.w_kind * kind, 4
            )
        return out
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_curator.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/agents/curator.py tests/test_curator.py
git commit -m "feat: heuristic curator scoring"
```

---

### Task 7: Scheduler (budget eviction, no compaction yet)

**Files:**
- Create: `lethe/core/scheduler.py`
- Test: `tests/test_scheduler.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_scheduler.py
from lethe.core.block import Block, BlockState
from lethe.adapters.fake import FakeTokenCounter
from lethe.agents.curator import Curator
from lethe.core.scheduler import Scheduler, Thresholds

def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)

def test_evicts_lowest_scored_until_under_budget():
    # window 100 tokens, budget 0.5 -> target 50 tokens. Each block "....."*8 = 40 chars=10 tok
    blocks = [_b(str(i), i, "x" * 40) for i in range(10)]  # 10 blocks * 10 tok = 100 tok
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=2))
    kept, evicted = sched.plan(blocks, now_step=9, goal="g")
    assert sum(FakeTokenCounter().count([b]) for b in kept) <= 50
    # the two most-recent steps are protected
    assert {"8", "9"}.issubset({b.id for b in kept})

def test_pinned_never_evicted():
    pinned = _b("keep", 0, "y" * 200); pinned.pinned = True
    filler = [_b(str(i), i, "x" * 40) for i in range(1, 6)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.3, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=1))
    kept, evicted = sched.plan([pinned, *filler], now_step=5, goal="g")
    assert "keep" in {b.id for b in kept}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.core.scheduler'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/core/scheduler.py
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
        protected_steps = set(sorted({b.created_step for b in blocks})[-self.th.keep_last_n_steps:])

        def protected(b: Block) -> bool:
            return b.pinned or b.created_step in protected_steps

        kept = list(blocks)
        target = self.target_tokens()
        # evict worst-scored non-protected blocks until under target
        evictable = sorted(
            (b for b in blocks if not protected(b)),
            key=lambda b: scores[b.id],
        )
        evicted: list[Block] = []
        idx = 0
        while self.tc.count(kept) > target and idx < len(evictable):
            victim = evictable[idx]; idx += 1
            kept.remove(victim); evicted.append(victim)
        return kept, evicted
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_scheduler.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/core/scheduler.py tests/test_scheduler.py
git commit -m "feat: scheduler budget eviction with pin and recency protection"
```

---

### Task 8: ContextManager (add / render / stats)

**Files:**
- Create: `lethe/core/manager.py`
- Modify: `lethe/__init__.py` (export `ContextManager`)
- Test: `tests/test_manager.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_manager.py
from lethe.core.block import Block, Message
from lethe.adapters.fake import FakeAdapter
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager

def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)

def make_cm():
    agent = FakeAdapter(context_window=100)
    return ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                          budget=0.5, triggers={"every_steps": 1, "on_budget": True})

def test_render_keeps_working_set_under_budget():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 40))   # 10 tok each -> 100 tok total
    msgs = ctx.render()
    used = ctx.stats()["tokens_with_lethe"]
    assert used <= 50
    assert all(isinstance(m, Message) for m in msgs)

def test_stats_reports_savings():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 40))
    ctx.render()
    s = ctx.stats()
    assert s["tokens_without_lethe"] == 100
    assert s["tokens_with_lethe"] <= 50
    assert s["evicted"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_manager.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'lethe.core.manager'`.

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/core/manager.py
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
        kept, evicted = self.cm.scheduler.plan(self.blocks, now_step=self.step, goal=self.goal)
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
        with_lethe = self.cm.agent.token_counter.count(self.blocks)
        all_blocks = self.blocks + [self.cm.store.get(h) for h in []]  # placeholder removed below
        return {
            "step": self.step,
            "tokens_with_lethe": with_lethe,
            "tokens_without_lethe": self._tokens_without(),
            "evicted": self._evicted,
            "faults": self._faults,
        }

    def _tokens_without(self) -> int:
        # sum of every block ever added (resident + paged)
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
            Curator(), agent.token_counter, budget=budget,
            context_window=agent.context_window, thresholds=thresholds,
        )

    def session(self, goal: str, subgoal: str | None = None) -> Session:
        return Session(self, goal, subgoal)

    def should_trigger(self, step: int) -> bool:
        every = self.triggers.get("every_steps")
        return bool(every) and step > 0 and step % every == 0
```

Note: remove the dead `all_blocks` placeholder line when typing it — keep only the `return`. Corrected `stats`:

```python
    def stats(self) -> dict:
        return {
            "step": self.step,
            "tokens_with_lethe": self.cm.agent.token_counter.count(self.blocks),
            "tokens_without_lethe": self._tokens_without(),
            "evicted": self._evicted,
            "faults": self._faults,
        }
```

- [ ] **Step 4: Export from package**

```python
# lethe/__init__.py
from lethe.core.manager import ContextManager
from lethe.core.block import Block, Message, BlockState

__all__ = ["ContextManager", "Block", "Message", "BlockState"]
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_manager.py -q`
Expected: PASS (2 passed).

- [ ] **Step 6: Commit**

```bash
git add lethe/core/manager.py lethe/__init__.py tests/test_manager.py
git commit -m "feat: ContextManager with sessions, budget GC, and stats"
```

**Milestone B complete:** a synthetic loop stays under budget; stats prove token reduction.

---

## Milestone C — Curator model judgment + Compactor (Phase 2)

### Task 9: Curator model-judgment blend

**Files:**
- Modify: `lethe/agents/curator.py`
- Test: `tests/test_curator.py` (add cases)

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_curator.py
from lethe.adapters.fake import FakeAdapter

def test_model_blend_overrides_toward_model_score():
    # model says 1.0 for everything; blend should lift a stale block's score
    adapter = FakeAdapter(handler=lambda msgs: "1.0")
    c = Curator(adapter=adapter, w_model=1.0, w_recency=0.0, w_refs=0.0, w_kind=0.0)
    old = _b("old", 0)
    s = c.score([old], now_step=100, goal="g")
    assert s["old"] == 1.0

def test_model_parse_clamps_bad_output():
    adapter = FakeAdapter(handler=lambda msgs: "not a number")
    c = Curator(adapter=adapter, w_model=1.0, w_recency=0.0, w_refs=0.0, w_kind=0.0)
    s = c.score([_b("x", 0)], now_step=1, goal="g")
    assert 0.0 <= s["x"] <= 1.0   # falls back safely (default keep-ish)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_curator.py -q`
Expected: FAIL (`Curator.__init__() got an unexpected keyword argument 'adapter'`).

- [ ] **Step 3: Extend implementation**

```python
# lethe/agents/curator.py  — replace the class with this version
from __future__ import annotations
from lethe.core.block import Block, Message

KIND_WEIGHT = {
    "note": 1.0, "text": 0.7, "file": 0.6, "tool_call": 0.6,
    "tool_result": 0.5, "image": 0.4,
}

def _parse_score(text: str, default: float = 0.5) -> float:
    try:
        v = float(text.strip().split()[0])
    except (ValueError, IndexError):
        return default
    return max(0.0, min(1.0, v))

class Curator:
    def __init__(self, adapter=None, w_recency: float = 0.5, w_refs: float = 0.25,
                 w_kind: float = 0.1, w_model: float = 0.15):
        self.adapter = adapter
        self.w_recency = w_recency
        self.w_refs = w_refs
        self.w_kind = w_kind
        self.w_model = w_model if adapter is not None else 0.0

    def score(self, blocks: list[Block], now_step: int, goal: str) -> dict[str, float]:
        ref_counts: dict[str, int] = {}
        for b in blocks:
            for r in b.refs:
                ref_counts[r] = ref_counts.get(r, 0) + 1
        span = max(now_step, 1)
        out: dict[str, float] = {}
        for b in blocks:
            if b.pinned:
                out[b.id] = 1.0
                continue
            recency = max(0.0, 1.0 - (now_step - b.created_step) / span)
            refs = min(1.0, ref_counts.get(b.id, 0) / 2.0)
            kind = KIND_WEIGHT.get(b.kind, 0.5)
            model = self._model_score(b, goal) if self.w_model else 0.0
            out[b.id] = round(
                self.w_recency * recency + self.w_refs * refs
                + self.w_kind * kind + self.w_model * model, 4
            )
        return out

    def _model_score(self, block: Block, goal: str) -> float:
        prompt = (f"Goal: {goal}\nBlock:\n{block.content}\n"
                  f"Rate 0.0-1.0 how relevant this block is to the goal. "
                  f"Reply with only the number.")
        resp = self.adapter.complete([Message(role="user",
                  blocks=[Block(id="q", role="user", kind="text",
                                content=prompt, created_step=0)])])
        return _parse_score(resp.text)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_curator.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Wire curator adapter into the Scheduler via ContextManager**

In `lethe/core/manager.py`, change the `Scheduler(Curator(), ...)` line to pass the curator adapter:

```python
        self.scheduler = Scheduler(
            Curator(adapter=self.curator_adapter), agent.token_counter, budget=budget,
            context_window=agent.context_window, thresholds=thresholds,
        )
```

- [ ] **Step 6: Run full suite**

Run: `python -m pytest -q`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add lethe/agents/curator.py lethe/core/manager.py tests/test_curator.py
git commit -m "feat: curator model-judgment blend with safe parsing"
```

---

### Task 10: Compactor (consolidation notes)

**Files:**
- Create: `lethe/agents/compactor.py`
- Test: `tests/test_compactor.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_compactor.py
from lethe.core.block import Block
from lethe.adapters.fake import FakeAdapter
from lethe.agents.compactor import Compactor

def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)

def test_compacts_cold_run_into_one_note():
    adapter = FakeAdapter(handler=lambda msgs: "SUMMARY: did steps 1-3")
    comp = Compactor(adapter)
    run = [_b("1", 1, "x" * 100), _b("2", 2, "y" * 100), _b("3", 3, "z" * 100)]
    note = comp.compact(run, session="s")
    assert note is not None
    assert note.covers == ["1", "2", "3"]
    assert "SUMMARY" in note.summary

def test_skips_when_no_savings():
    adapter = FakeAdapter(handler=lambda msgs: "x" * 1000)  # summary bigger than originals
    comp = Compactor(adapter)
    run = [_b("1", 1, "tiny")]
    note = comp.compact(run, session="s")
    assert note is None

def test_never_compacts_pinned():
    adapter = FakeAdapter(handler=lambda msgs: "SUMMARY")
    comp = Compactor(adapter)
    pinned = _b("p", 1, "x" * 100); pinned.pinned = True
    note = comp.compact([pinned], session="s")
    assert note is None
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_compactor.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'lethe.agents.compactor'`).

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/agents/compactor.py
from __future__ import annotations
import uuid
from lethe.core.block import Block, Message
from lethe.stores.base import Note

class Compactor:
    def __init__(self, adapter):
        self.adapter = adapter

    def compact(self, run: list[Block], session: str) -> Note | None:
        if not run or any(b.pinned for b in run):
            return None
        joined = "\n---\n".join(b.content for b in run)
        prompt = ("Summarize these completed agent steps. Preserve decisions, results, "
                  "and any open threads. Be dense.\n\n" + joined)
        summary = self.adapter.complete([Message(role="user",
                    blocks=[Block(id="q", role="user", kind="text",
                                  content=prompt, created_step=0)])]).text
        orig_tokens = self.adapter.token_counter.count(run)
        note_block = Block(id="n", role="assistant", kind="note",
                           content=summary, created_step=run[-1].created_step)
        note_tokens = self.adapter.token_counter.count([note_block])
        if note_tokens >= orig_tokens:        # no negative-savings compaction
            return None
        return Note(id=str(uuid.uuid4())[:8], session=session,
                    summary=summary, covers=[b.id for b in run], tokens=note_tokens)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_compactor.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/agents/compactor.py tests/test_compactor.py
git commit -m "feat: compactor consolidation notes with guardrails"
```

**Milestone C complete:** curator can use a model; compactor produces notes safely.

---

## Milestone D — Archivist + paging + needle (Phase 3)

### Task 11: SqliteStore (FTS5)

**Files:**
- Create: `lethe/stores/sqlite.py`
- Test: `tests/test_sqlite_store.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_sqlite_store.py
from lethe.core.block import Block
from lethe.stores.sqlite import SqliteStore

def _b(id, content, handle=None, step=0):
    return Block(id=id, role="tool", kind="tool_result", content=content,
                 created_step=step, handle=handle)

def test_roundtrip_by_handle(tmp_path):
    s = SqliteStore(str(tmp_path / "t.db"))
    s.put(_b("1", "config contents", handle="a3f9"))
    got = s.get("a3f9")
    assert got is not None and got.content == "config contents"

def test_fts_search(tmp_path):
    s = SqliteStore(str(tmp_path / "t.db"))
    s.put(_b("1", "the secret needle is 4242", handle="h1"))
    s.put(_b("2", "unrelated log line", handle="h2"))
    hits = s.search("needle", limit=5)
    assert "1" in {h.id for h in hits}
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_sqlite_store.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'lethe.stores.sqlite'`).

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/stores/sqlite.py
from __future__ import annotations
import json, sqlite3
from lethe.core.block import Block, BlockState
from lethe.stores.base import Note

class SqliteStore:
    def __init__(self, path: str = "./lethe.db"):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS blocks(
            id TEXT PRIMARY KEY, session TEXT, role TEXT, kind TEXT, content TEXT,
            created_step INT, pinned INT, tokens INT, state TEXT, handle TEXT, meta TEXT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS notes(
            id TEXT PRIMARY KEY, session TEXT, summary TEXT, covers TEXT, tokens INT)""")
        self.db.execute("""CREATE TABLE IF NOT EXISTS events(
            ts TEXT, session TEXT, kind TEXT, payload TEXT)""")
        self.db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS blocks_fts
            USING fts5(id UNINDEXED, content)""")
        self.db.commit()

    def put(self, block: Block) -> None:
        self.db.execute("REPLACE INTO blocks VALUES (?,?,?,?,?,?,?,?,?,?,?)", (
            block.id, block.meta.get("session", ""), block.role, block.kind, block.content,
            block.created_step, int(block.pinned), block.tokens,
            block.state.value, block.handle, json.dumps(block.meta)))
        self.db.execute("DELETE FROM blocks_fts WHERE id=?", (block.id,))
        self.db.execute("INSERT INTO blocks_fts(id, content) VALUES (?,?)",
                        (block.id, block.content))
        self.db.commit()

    def _row_to_block(self, row) -> Block:
        return Block(id=row[0], role=row[2], kind=row[3], content=row[4],
                     created_step=row[5], pinned=bool(row[6]), tokens=row[7],
                     state=BlockState(row[8]), handle=row[9], meta=json.loads(row[10] or "{}"))

    def get(self, handle: str) -> Block | None:
        cur = self.db.execute("SELECT * FROM blocks WHERE handle=?", (handle,))
        row = cur.fetchone()
        return self._row_to_block(row) if row else None

    def search(self, query: str, limit: int) -> list[Block]:
        cur = self.db.execute(
            "SELECT b.* FROM blocks_fts f JOIN blocks b ON b.id=f.id "
            "WHERE blocks_fts MATCH ? LIMIT ?", (query, limit))
        return [self._row_to_block(r) for r in cur.fetchall()]

    def put_note(self, note: Note) -> None:
        self.db.execute("REPLACE INTO notes VALUES (?,?,?,?,?)",
            (note.id, note.session, note.summary, json.dumps(note.covers), note.tokens))
        self.db.commit()

    def events(self, kind: str, payload: dict) -> None:
        self.db.execute("INSERT INTO events VALUES (datetime('now'), ?, ?, ?)",
                        (payload.get("session", ""), kind, json.dumps(payload)))
        self.db.commit()
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_sqlite_store.py -q`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/stores/sqlite.py tests/test_sqlite_store.py
git commit -m "feat: sqlite store with FTS5 lexical search"
```

---

### Task 12: Archivist (page-out, page-fault, recall)

**Files:**
- Create: `lethe/agents/archivist.py`
- Test: `tests/test_archivist.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_archivist.py
from lethe.core.block import Block, BlockState
from lethe.stores.memory import MemoryStore
from lethe.agents.archivist import Archivist, make_handle

def _b(id, content, step=0):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)

def test_page_out_sets_handle_state_and_stub():
    store = MemoryStore(); arch = Archivist(store)
    b = _b("1", "big config file contents", step=5)
    stub = arch.page_out(b)
    assert b.state is BlockState.PAGED
    assert b.handle is not None
    assert "paged" in stub.content and b.handle in stub.content
    assert store.get(b.handle).content == "big config file contents"

def test_page_fault_by_handle_restores():
    store = MemoryStore(); arch = Archivist(store)
    b = _b("1", "secret needle 4242", step=5)
    arch.page_out(b)
    got = arch.page_fault(b.handle)
    assert got is not None and got.content == "secret needle 4242"
    assert got.state is BlockState.REHYDRATED

def test_recall_lexical_finds_block():
    store = MemoryStore(); arch = Archivist(store)
    arch.page_out(_b("1", "the needle is 4242", step=1))
    hits = arch.recall("needle")
    assert hits and hits[0].content == "the needle is 4242"
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_archivist.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'lethe.agents.archivist'`).

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/agents/archivist.py
from __future__ import annotations
import uuid
from lethe.core.block import Block, BlockState

def make_handle() -> str:
    return uuid.uuid4().hex[:4]

class Archivist:
    def __init__(self, store):
        self.store = store

    def page_out(self, block: Block) -> Block:
        if block.handle is None:
            block.handle = make_handle()
        block.state = BlockState.PAGED
        self.store.put(block)
        self.store.events("page_out", {"id": block.id, "handle": block.handle})
        label = block.meta.get("label", f"{block.kind} @step{block.created_step}")
        return Block(id=f"stub-{block.id}", role=block.role, kind="text",
                     content=f"[paged: {label} · handle={block.handle}]",
                     created_step=block.created_step,
                     handle=block.handle, meta={"stub_for": block.id})

    def page_fault(self, handle: str) -> Block | None:
        block = self.store.get(handle)
        if block is None:
            return None
        block.state = BlockState.REHYDRATED
        self.store.events("page_fault", {"handle": handle})
        return block

    def recall(self, query: str, limit: int = 5) -> list[Block]:
        return self.store.search(query, limit=limit)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_archivist.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/agents/archivist.py tests/test_archivist.py
git commit -m "feat: archivist page-out, page-fault, lexical recall"
```

---

### Task 13: Wire Archivist + observe + recall into ContextManager

**Files:**
- Modify: `lethe/core/manager.py`
- Test: `tests/test_manager.py` (add cases)

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_manager.py
def test_observe_referenced_handle_pages_block_back_in():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 40))
    ctx.render()
    # find a paged handle from the store
    paged = list(cm.store._by_handle.keys())
    assert paged
    h = paged[0]
    from lethe.adapters.base import Response
    ctx.observe(Response(text=f"I need handle={h} again"))
    assert any(b.handle == h for b in ctx.blocks)   # rehydrated into working set

def test_recall_query_returns_block():
    cm = make_cm()
    ctx = cm.session(goal="g")
    ctx.add(_b("needle", 0, "the needle is 4242"))
    for i in range(1, 12):
        ctx.add(_b(str(i), i, "x" * 40))
    ctx.render()
    got = ctx.recall("needle")
    assert got is not None and "4242" in got.content
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_manager.py -q`
Expected: FAIL (`'Session' object has no attribute 'observe'`).

- [ ] **Step 3: Extend Session in `manager.py`**

Add an Archivist to `Session._gc` paging and add `observe`/`recall`. Replace the relevant parts of `Session`:

```python
# at top of manager.py imports
from lethe.agents.archivist import Archivist
import re

# in Session.__init__ add:
        self.archivist = Archivist(cm.store)

# replace Session._gc with:
    def _gc(self) -> None:
        kept, evicted = self.cm.scheduler.plan(self.blocks, now_step=self.step, goal=self.goal)
        stubs = []
        for b in evicted:
            stub = self.archivist.page_out(b)
            stubs.append(stub)
        self._evicted += len(evicted)
        self.blocks = kept + stubs

# add to Session:
    def observe(self, response) -> None:
        for h in set(re.findall(r"handle=([0-9a-f]{4})", response.text)):
            block = self.archivist.page_fault(h)
            if block and not any(b.id == block.id for b in self.blocks):
                self.blocks.append(block)
                self._faults += 1
                # drop the stub for this handle
                self.blocks = [b for b in self.blocks
                               if b.meta.get("stub_for") != block.id]

    def recall(self, query_or_handle: str):
        if re.fullmatch(r"[0-9a-f]{4}", query_or_handle):
            return self.archivist.page_fault(query_or_handle)
        hits = self.archivist.recall(query_or_handle)
        return hits[0] if hits else None
```

Note: stubs count as tokens too, so `_tokens_without` already excludes them (they live only in `self.blocks`, not the store). Keep `_tokens_without` summing store blocks + resident real blocks; stubs are tiny and acceptable overhead.

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_manager.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/core/manager.py tests/test_manager.py
git commit -m "feat: paging stubs, observe page-faults, recall in ContextManager"
```

---

### Task 14: Needle test (the value proof)

**Files:**
- Create: `lethe/evals/needle.py`
- Test: `tests/test_needle.py`

- [ ] **Step 1: Write the needle driver**

```python
# lethe/evals/needle.py
from lethe.core.block import Block
from lethe.adapters.fake import FakeAdapter
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager

NEEDLE = "the launch code is 4242"

def run_needle(steps: int = 50) -> dict:
    agent = FakeAdapter(context_window=400)
    cm = ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="find the launch code later")
    ctx.add(Block(id="needle", role="user", kind="text", content=NEEDLE, created_step=0))
    for i in range(1, steps):
        ctx.add(Block(id=f"noise{i}", role="tool", kind="tool_result",
                      content="filler " * 20, created_step=i))
        ctx.render()
    recalled = ctx.recall("launch code")
    s = ctx.stats()
    s["needle_recovered"] = bool(recalled and "4242" in recalled.content)
    return s
```

- [ ] **Step 2: Write the failing test**

```python
# tests/test_needle.py
from lethe.evals.needle import run_needle

def test_needle_survives_compaction():
    s = run_needle(steps=50)
    assert s["needle_recovered"] is True
    assert s["tokens_with_lethe"] <= 0.5 * 400 + 50   # under budget (+ small stub slack)
    assert s["tokens_without_lethe"] > s["tokens_with_lethe"]
```

- [ ] **Step 3: Run to verify it passes**

Run: `python -m pytest tests/test_needle.py -q`
Expected: PASS (1 passed). If the needle is evicted (recovered False), that's the real signal to debug eviction protection — see systematic-debugging.

- [ ] **Step 4: Run full suite**

Run: `python -m pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add lethe/evals/needle.py tests/test_needle.py
git commit -m "feat: needle-in-haystack eval proving lossless recall under budget"
```

**Milestone D complete:** the core thesis is proven by a passing needle test.

---

## Milestone E — Live visualizer + real Claude

### Task 15: Live console visualizer

**Files:**
- Create: `lethe/viz/console.py`
- Test: `tests/test_viz.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_viz.py
from lethe.core.block import Block, BlockState
from lethe.viz.console import render_frame

def _b(id, step, content, state=BlockState.ACTIVE, pinned=False, handle=None):
    b = Block(id=id, role="tool", kind="tool_result", content=content,
              created_step=step, state=state, pinned=pinned, handle=handle)
    return b

def test_frame_shows_states_and_budget():
    blocks = [
        _b("g", 0, "goal", pinned=True),
        _b("a", 9, "recent"),
        _b("stub-1", 5, "[paged: file @step5 · handle=a3f9]", state=BlockState.PAGED, handle="a3f9"),
    ]
    frame = render_frame(blocks, goal="Refactor login", step=9,
                         used_tokens=58, budget_tokens=60,
                         stats={"tokens_without_lethe": 184, "tokens_with_lethe": 58})
    assert "Refactor login" in frame
    assert "PIN" in frame
    assert "paged" in frame
    assert "%" in frame   # budget bar percentage
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_viz.py -q`
Expected: FAIL (`ModuleNotFoundError: No module named 'lethe.viz.console'`).

- [ ] **Step 3: Write minimal implementation**

```python
# lethe/viz/console.py
from __future__ import annotations
from lethe.core.block import Block, BlockState

def _bar(used: int, budget: int, width: int = 18) -> str:
    frac = 0.0 if budget == 0 else min(1.0, used / budget)
    filled = int(frac * width)
    pct = int(frac * 100)
    return "#" * filled + "." * (width - filled) + f"  {pct}% de presupuesto"

def _tag(b: Block) -> str:
    if b.pinned:
        return "PIN   "
    if b.state is BlockState.PAGED:
        return "[paged]"
    if b.kind == "note":
        return "NOTE  "
    if b.state is BlockState.WARM:
        return "WARM  "
    return "ACTIVE"

def render_frame(blocks: list[Block], goal: str, step: int,
                 used_tokens: int, budget_tokens: int, stats: dict | None = None) -> str:
    lines = [f'Paso {step} · Objetivo: "{goal}"',
             f"Pizarra: {_bar(used_tokens, budget_tokens)}", ""]
    for b in blocks:
        preview = b.content.replace("\n", " ")[:48]
        lines.append(f"{_tag(b)}  paso {b.created_step:>3}  {preview}")
    if stats:
        lines += ["", (f"sin LETHE: {stats['tokens_without_lethe']} tok  ·  "
                       f"con LETHE: {stats['tokens_with_lethe']} tok")]
    return "\n".join(lines)
```

- [ ] **Step 4: Run to verify pass**

Run: `python -m pytest tests/test_viz.py -q`
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add lethe/viz/console.py tests/test_viz.py
git commit -m "feat: live console visualizer for working set and budget"
```

---

### Task 16: AnthropicAdapter (real Claude)

**Files:**
- Create: `lethe/adapters/anthropic.py`

- [ ] **Step 1: Write minimal implementation (no unit test — needs network/key)**

```python
# lethe/adapters/anthropic.py
from __future__ import annotations
from functools import lru_cache
from math import ceil
from lethe.core.block import Block, Message
from lethe.adapters.base import Response

class _AnthropicTokenCounter:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    @lru_cache(maxsize=4096)
    def _count_text(self, text: str) -> int:
        try:
            r = self.client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": text or " "}])
            return r.input_tokens
        except Exception:
            return max(1, ceil(len(text) / 4))   # offline fallback

    def count(self, blocks: list[Block]) -> int:
        return sum(self._count_text(b.content) for b in blocks)

class AnthropicAdapter:
    name = "claude"

    def __init__(self, model: str = "claude-haiku-4-5", context_window: int = 200_000,
                 api_key: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.context_window = context_window
        self.token_counter = _AnthropicTokenCounter(self.client, model)

    def _to_native(self, messages: list[Message]) -> list[dict]:
        out = []
        for m in messages:
            text = "\n".join(b.content for b in m.blocks)
            role = "assistant" if m.role == "assistant" else "user"
            out.append({"role": role, "content": text})
        return out

    def complete(self, messages: list[Message], max_tokens: int = 1024, **kw) -> Response:
        r = self.client.messages.create(
            model=self.model, max_tokens=max_tokens,
            messages=self._to_native(messages))
        text = "".join(part.text for part in r.content if getattr(part, "type", "") == "text")
        return Response(text=text, raw=r)
```

- [ ] **Step 2: Verify import without key (class import only)**

Run: `python -c "import lethe.adapters.anthropic; print('ok')"`
Expected: `ok` (importing the module must not require the SDK to be installed at import time — the `import anthropic` is inside `__init__`).

- [ ] **Step 3: Commit**

```bash
git add lethe/adapters/anthropic.py
git commit -m "feat: real AnthropicAdapter with cached token counting"
```

---

### Task 17: Example loop + README

**Files:**
- Create: `lethe/examples/claude_loop.py`
- Create: `README.md`

- [ ] **Step 1: Write the example**

```python
# lethe/examples/claude_loop.py
"""Run a long synthetic loop against real Claude and watch LETHE manage context.

Usage:
    set ANTHROPIC_API_KEY=...   (PowerShell: $env:ANTHROPIC_API_KEY="...")
    python -m lethe.examples.claude_loop
"""
import os
from lethe.core.block import Block
from lethe.stores.sqlite import SqliteStore
from lethe.core.manager import ContextManager
from lethe.viz.console import render_frame

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY to run the real loop."); return
    from lethe.adapters.anthropic import AnthropicAdapter
    agent = AnthropicAdapter(model="claude-opus-4-8")
    curator = AnthropicAdapter(model="claude-haiku-4-5")
    cm = ContextManager(agent=agent, curator=curator,
                        store=SqliteStore("./lethe.db"),
                        budget=0.5, triggers={"every_steps": 3, "on_budget": True})
    ctx = cm.session(goal="Track the launch code through a long task")
    ctx.add(Block(id="needle", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))
    for i in range(1, 30):
        ctx.add(Block(id=f"s{i}", role="tool", kind="tool_result",
                      content=f"step {i} produced some verbose output " * 10, created_step=i))
        ctx.render()
        s = ctx.stats()
        print("\n" + render_frame(ctx.blocks, goal=ctx.goal, step=i,
              used_tokens=s["tokens_with_lethe"],
              budget_tokens=int(agent.context_window * 0.5), stats=s))
    print("\nRecall:", ctx.recall("launch code"))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Write `README.md`** (hero paragraph from spec + quickstart)

```markdown
# LETHE

Live Ephemeral Token & History Engine — a context garbage collector for long-running LLM
agents. It scores each context block's relevance to the current goal, compacts finished
work into dense notes, and pages cold material to a store — losslessly, so anything can be
recalled on demand.

## Quickstart (no API key)

    python -m pytest -q          # run the full test suite incl. the needle test

## Real Claude demo

    $env:ANTHROPIC_API_KEY="sk-..."   # PowerShell
    python -m lethe.examples.claude_loop
```

- [ ] **Step 3: Run full suite a final time**

Run: `python -m pytest -q`
Expected: all green.

- [ ] **Step 4: Commit**

```bash
git add lethe/examples/claude_loop.py README.md
git commit -m "docs: example claude loop and README"
```

**Milestone E complete:** visualizer renders frames; real adapter ready; example runnable.

---

## Self-review notes

- **Spec coverage:** types (T2), PAL/fake (T3–T4), store+lexical (T5,T11), curator heuristic+model (T6,T9), scheduler+budget (T7), manager API add/render/observe/recall/pin/stats (T8,T13), compactor (T10), archivist paging+fault (T12), needle eval (T14), visualizer (T15), real Claude adapter (T16), example+README (T17). All slice scope sections map to a task.
- **Type consistency:** `Block`, `Message`, `BlockState`, `Note`, `Response`, `TokenCounter`, `Store`, `Curator.score(blocks, now_step, goal)`, `Scheduler.plan(...) -> (kept, evicted)`, `Archivist.page_out/page_fault/recall`, `render_frame(...)` used identically across tasks.
- **Deferred (later phases, not this plan):** multi-provider adapters, ensemble, embeddings/vss, MCP, transparent `wrap()`, full eval harness.
```
