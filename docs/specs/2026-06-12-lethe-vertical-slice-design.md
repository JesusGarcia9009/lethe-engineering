# LETHE v0.1 — Vertical Slice Design Spec

**Live Ephemeral Token & History Engine — first buildable slice**

> Status: approved design · Target builder: Claude Code · Date: 2026-06-12
> Parent design: `LETHE_engineering_design.md`
> Scope: a single-provider, end-to-end vertical slice that proves the core value
> (token reduction without quality loss) before investing in multi-provider, ensemble,
> embeddings, MCP, or transparent `wrap()`.

---

## 1. Purpose

Prove the central thesis of LETHE with the smallest end-to-end system that exercises the
**full block lifecycle**: a long-running agent loop adds context blocks, LETHE scores them
for relevance to the current goal, compacts finished work into dense notes, and pages cold
material to an external store — losslessly, so anything can be recalled on demand.

Success = the **needle test** passes: a fact planted early, after forced compaction and
paging, is correctly recalled ~50 steps later, while total tokens stay under budget.

This slice is a foundation: every interface is provider-agnostic so later phases
(multi-provider, ensemble curator, embeddings, MCP) plug in without rework.

---

## 2. Scope

### In scope
- **Single provider:** Claude via `AnthropicAdapter`, plus a deterministic `FakeAdapter`
  for tests/TDD.
- **Full block lifecycle:** `ACTIVE → WARM → COMPACTED → PAGED → REHYDRATED`, with `PINNED`
  excluded from the machine.
- **Curator:** heuristic scoring (recency, reference count, kind weights, pins) blended
  with a single cheap model judgment.
- **Compactor:** consolidation notes replacing contiguous cold runs, with provenance
  handles to originals.
- **Archivist:** SQLite store (source of truth) + **handle + lexical** retrieval (no
  embeddings). Page-out, stub, page-fault.
- **Scheduler:** policy engine with `every_steps` and `on_budget` triggers; deterministic
  given scores.
- **Public API (explicit/full-control):** `ContextManager`, `session`, `add`, `render`,
  `observe`, `recall`, `pin`/`unpin`, `stats`.
- **Eval:** the needle-in-haystack test.
- **Example:** a real Claude loop.
- **Live console visualizer:** an optional terminal view that renders the working set in
  real time as the loop runs — block states (ACTIVE / WARM / NOTE / paged / PIN), a budget
  bar, and a running stats line — so a human can *watch* compaction and paging happen.

### Out of scope (later phases)
- Multi-provider adapters (GPT, Gemini, Llama, Hermes).
- Ensemble curator / cross-provider voting / uncertainty biasing.
- Embeddings + vector search (sqlite-vss). Retrieval is handle + lexical only.
- MCP adapter for Claude Code.
- Transparent `wrap()` middleware.
- Full eval harness (LoCoMo, SWE tasks, ablations, latency dashboards).
- Learned/trained curator scoring.

---

## 3. Architecture

```
lethe/
  core/
    block.py        # Block, Message, BlockState(enum) — pure types, no deps
    manager.py      # ContextManager: session, add, render, observe, recall, pin, stats
    scheduler.py    # policy engine: score -> decide -> compact -> page
  adapters/
    base.py         # ProviderAdapter (Protocol), Response, TokenCounter
    fake.py         # deterministic FakeAdapter (tests + TDD)
    anthropic.py    # real AnthropicAdapter (Claude)
  agents/
    curator.py      # scoring: heuristics (recency, refs, kind, pins) + single model
    compactor.py    # consolidation notes for cold contiguous runs
    archivist.py    # page-out / stub / page-fault, lexical search
  stores/
    sqlite.py       # source of truth + lexical search (sqlite FTS5)
    memory.py       # in-memory store for tests
  viz/
    console.py      # live terminal view: working set, states, budget bar, stats
  evals/
    needle.py       # plant fact -> force compaction -> recall ~50 steps later
  examples/
    claude_loop.py  # real loop against Claude (can render the live view)
  pyproject.toml  README.md
```

### Boundary rules (design for isolation)
- `core/block.py` depends on nothing — pure dataclasses/enums.
- Agents (`curator`, `compactor`, `archivist`) depend only on the **abstract**
  `ProviderAdapter` and `Store` interfaces, never on `anthropic` directly.
- The store is swappable: `memory.py` for fast tests, `sqlite.py` for real runs. Both
  implement the same `Store` interface.
- Token counting is abstracted behind `TokenCounter`; the eviction engine never assumes a
  specific provider's tokenizer.

Each unit answers: *what does it do, how is it used, what does it depend on.*

---

## 4. Core types (`core/block.py`)

```python
class BlockState(Enum):
    ACTIVE = "active"        # resident in working set
    WARM = "warm"            # resident, candidate for compaction
    COMPACTED = "compacted"  # represented by a consolidation note; detail in store
    PAGED = "paged"          # only a stub in context; full content in store
    REHYDRATED = "rehydrated"# pulled back to ACTIVE after a fault

@dataclass
class Block:
    id: str
    role: Literal["system","user","assistant","tool","reasoning"]
    kind: Literal["text","tool_call","tool_result","file","image","note"]
    content: str
    created_step: int
    pinned: bool = False
    state: BlockState = BlockState.ACTIVE
    tokens: int | None = None                       # filled by TokenCounter
    handle: str | None = None                       # stable retrieval id
    refs: list[str] = field(default_factory=list)   # blocks this one cites
    meta: dict = field(default_factory=dict)        # path, tool name, etc.

@dataclass
class Message:                                       # provider-neutral
    role: str
    blocks: list[Block]
```

`handle` is a short stable id (e.g. `a3f9`) shown inside stubs:
`[paged: read config.py @step12 · handle=a3f9]`.

---

## 5. Adapter layer (`adapters/`)

### 5.1 `base.py`

```python
class TokenCounter(Protocol):
    def count(self, blocks: list[Block]) -> int: ...

@dataclass
class Response:
    text: str
    raw: Any = None

class ProviderAdapter(Protocol):
    name: str
    context_window: int
    token_counter: TokenCounter
    def complete(self, messages: list[Message], **kw) -> Response: ...
```

### 5.2 `fake.py` — `FakeAdapter`
Deterministic, no network. Used for all unit tests and TDD.
- `token_counter`: deterministic approximation (e.g. `ceil(len(content)/4)` or word count)
  so eviction math is reproducible.
- `complete()`: returns scripted/templated responses. For curator tests it returns scores
  driven by a rule the test controls (e.g. "blocks containing NEEDLE score 1.0"); for
  compactor tests it returns a fixed summary template.

### 5.3 `anthropic.py` — `AnthropicAdapter`
Real Claude via the `anthropic` SDK.
- `token_counter`: uses Anthropic `count_tokens` endpoint, **cached** per block content to
  avoid repeated network calls. Falls back to the `/4` approximation if offline.
- `complete()`: Messages API. Model id from config (default `claude-haiku-4-5` for
  curator/compactor to keep cost low; the *agent* in the example uses a larger model).
- API key from `ANTHROPIC_API_KEY` env var.

> Eviction accuracy: the engine does not require provider-exact token counts to function;
> any consistent `TokenCounter` keeps the working set under budget. Real counts (Anthropic
> endpoint) are used in the example; the deterministic counter is used in tests.

---

## 6. Store layer (`stores/`)

Common `Store` interface:

```python
class Store(Protocol):
    def put(self, block: Block) -> None: ...            # upsert source of truth
    def get(self, handle: str) -> Block | None: ...     # page-fault by handle
    def search(self, query: str, limit: int) -> list[Block]: ...  # lexical
    def put_note(self, note: Note) -> None: ...
    def events(self, kind: str, payload: dict) -> None: ...  # audit log
```

- `memory.py`: dicts; `search` is a simple case-insensitive substring/keyword match.
- `sqlite.py`: tables `blocks`, `refs`, `notes`, `events`; lexical search via SQLite
  **FTS5** virtual table over block content. No vector table in the slice.

```sql
CREATE TABLE blocks (
  id TEXT PRIMARY KEY, session TEXT, role TEXT, kind TEXT,
  content TEXT, created_step INT, pinned INT, tokens INT,
  state TEXT, handle TEXT, meta TEXT  -- meta as JSON
);
CREATE TABLE refs  (src TEXT, dst TEXT);
CREATE TABLE notes (id TEXT PRIMARY KEY, session TEXT, summary TEXT, covers TEXT, tokens INT);
CREATE TABLE events (ts TEXT, session TEXT, kind TEXT, payload TEXT);
CREATE VIRTUAL TABLE blocks_fts USING fts5(handle UNINDEXED, content);
```

---

## 7. Agents (`agents/`)

### 7.1 Curator (`curator.py`)
Produces a relevance score `0..1` per non-pinned block against the current goal/subgoal.

- **Heuristic features (no model call):**
  - recency: decay with `created_step` distance from now.
  - reference count: blocks cited by later blocks (via `refs`) get a strong keep boost.
  - kind weights: e.g. hard constraint/note > verbose `tool_result` dump.
  - pins → forced `1.0` (and excluded from eviction entirely).
- **Model judgment (single cheap call):** the adapter rates each candidate block's
  relevance to the stated goal. Batched into one prompt where practical.
- **Blend:** `score = w_h * heuristic + w_m * model` with configurable weights. In the
  slice, heuristic-first; model call only on triggers.

### 7.2 Compactor (`compactor.py`)
When a contiguous run of *completed* low-score (cold) blocks exists, replace it with one
**consolidation note** preserving decisions, results, and open threads, plus handles to the
originals.
- Guardrails: never compact across an unresolved subgoal boundary; never compact pinned
  blocks; skip if the note isn't meaningfully smaller than the originals (no
  negative-savings compaction).

### 7.3 Archivist (`archivist.py`)
Owns paging against the `Store`.
- **page-out:** write block to store, set state `PAGED`, leave a one-line stub in context.
- **page-fault:** on a referenced handle (from `observe`) or an explicit `recall`, load the
  block back, set `REHYDRATED`/`ACTIVE`.
- **lexical retrieval:** `recall(query)` runs `store.search` and pages in top hits.
- **provenance:** every stub and consolidation note resolves back to original content.

---

## 8. Scheduler (`core/scheduler.py`)

On a trigger (`budget exceeded`, `every K steps`, or explicit `compact()`):

1. **score** — Curator scores all non-pinned blocks.
2. **decide** — apply thresholds: `score < warm` → WARM; completed run with `score < cold`
   → eligible for compaction.
3. **compact** — Compactor consolidates eligible cold runs.
4. **page** — Archivist pages out cold/compacted blocks until working set ≤ budget.

Deterministic given scores → testable and reproducible. Safety: `keep_last_n_steps`
always stay ACTIVE; `never_compact_open_subgoal`.

Default thresholds (config): `warm: 0.45`, `cold: 0.25`, `fault_in: 0.7`,
`keep_last_n_steps: 3`, `budget: 0.6`.

---

## 9. Public API (`core/manager.py`)

Explicit / full-control integration (section 8.1 of the parent doc):

```python
from lethe import ContextManager
from lethe.adapters import AnthropicAdapter

cm = ContextManager(
    agent=AnthropicAdapter(model="claude-opus-4-8"),
    curator=AnthropicAdapter(model="claude-haiku-4-5"),
    budget=0.6,
    store="sqlite:///./lethe.db",
    triggers={"every_steps": 5, "on_budget": True},
)

ctx = cm.session(goal="Refactor the auth module to use JWT")
ctx.add(block)                 # feed tool outputs / file reads / turns
working_set = ctx.render()     # compacted, provider-ready messages
response = cm.agent.complete(working_set)
ctx.observe(response)          # records which handles were referenced -> may page-fault
```

Methods:
- `ctx.add(block)` / `ctx.pin(block_id)` / `ctx.unpin(block_id)`
- `ctx.render() -> list[Message]`
- `ctx.recall(handle | query) -> Block` — manual page-in
- `ctx.observe(response)` — record referenced handles, trigger faults
- `ctx.stats() -> dict` — tokens saved, faults, evictions, scores
- `cm.session(goal, subgoal=None)`

---

## 10. Testing strategy (TDD)

Test-first with `FakeAdapter` + `memory.py` store. Each unit gets tests before
implementation:

- **block** — lifecycle transitions, pin exclusion.
- **token counting** — deterministic counter math.
- **curator** — heuristic features (recency, refs, kind, pins); blend with scripted model
  scores; pins forced to 1.0.
- **compactor** — cold-run consolidation; guardrails (no cross-subgoal, no pinned, no
  negative-savings).
- **archivist** — page-out leaves stub; page-fault by handle restores content; lexical
  `recall` finds planted text.
- **scheduler** — deterministic decide/compact/page given fixed scores; budget respected;
  `keep_last_n_steps`.
- **manager** — end-to-end `add/render/observe/recall/stats`.
- **needle (eval)** — plant a fact at step ~1, run a ~50-step synthetic loop that forces
  compaction and paging, then query it; assert the fact is recalled via page-fault and the
  working set stayed under budget throughout.

A real-Claude smoke example (`examples/claude_loop.py`) is runnable manually with an API
key but is not part of the deterministic test suite.

---

## 10b. Live console visualizer (`viz/console.py`)

A read-only renderer that turns a `ContextManager` snapshot into a terminal view. It does
not change any logic — it only *displays* state, so it is decoupled from the engine and can
be omitted entirely without affecting behavior.

Responsibilities:
- Render the current working set, one line per block, tagged by state:
  `ACTIVE`, `WARM`, `NOTE` (consolidation note), `[paged]` (stub + handle), `PIN`.
- Render a **budget bar** showing working-set size vs the budget fraction.
- Render a one-line running **stats** strip (step, tokens with/without LETHE, paged count,
  faults, needle-recovered yes/no).
- Update each step when called from the loop (simple reprint; no curses dependency required
  in the slice — plain ANSI/printed frames are enough).

Example frame:

```
Paso 23 · Objetivo: "Refactorizar login"
Pizarra: ###########.......  58% de 60% presupuesto

ACTIVE     paso 21  leer auth.py
ACTIVE     paso 22  resultado test
ACTIVE     paso 23  <- turno actual
NOTE       resumen de pasos 8-15  (reemplazo 8 bloques)
[paged]    config.json @paso5 · handle=a3f9
[paged]    log viejo @paso11 · handle=b2c1
PIN        objetivo de la tarea
```

It consumes only public `ContextManager` data (the same data `stats()` and `render()`
expose), so it needs no special hooks. Tested by asserting the rendered string contains the
expected state tags for a known working set — no live terminal needed in tests.

## 11. Configuration

```yaml
lethe:
  budget: 0.6
  agent:   { provider: claude, model: claude-opus-4-8 }
  curator: { provider: claude, model: claude-haiku-4-5, mode: blend }
  compactor: { provider: claude, model: claude-haiku-4-5 }
  store:   { backend: sqlite, path: ./lethe.db }   # FTS5 lexical, no vectors
  triggers:   { every_steps: 5, on_budget: true }
  thresholds: { warm: 0.45, cold: 0.25, fault_in: 0.7 }
  safety:     { keep_last_n_steps: 3, never_compact_open_subgoal: true }
```

In-code config (dataclass) is the source of truth; YAML loading is optional convenience.

---

## 12. Dependencies

- Runtime: `anthropic` (SDK) + Python stdlib (`sqlite3` with FTS5, `dataclasses`, `json`).
- Dev/test: `pytest`. No vector DB, no embeddings, no extra providers in the slice.
- Python 3.14 (verified available locally).

---

## 13. Acceptance criteria

1. All unit tests pass with `FakeAdapter` (no network).
2. **Needle test passes:** planted fact recalled ~50 steps later after forced compaction
   and paging; working set stayed ≤ budget throughout.
3. `stats()` reports positive token reduction vs a no-GC baseline run on the same loop.
4. Lossless: any compacted/paged block is recoverable by handle and by lexical `recall`.
5. `examples/claude_loop.py` runs end-to-end against real Claude with an API key set.
6. The live visualizer renders a working set with correct state tags and a budget bar, and
   can be attached to the example loop to watch compaction/paging in real time.

---

## 14. Risks (slice-level)

- **Over-eviction.** Mitigations: lossless paging, `keep_last_n_steps`, never compact open
  subgoal, conservative thresholds.
- **Curator cost eating savings.** Mitigations: heuristic-first, cheap model (Haiku), score
  only on triggers; `stats()` surfaces net savings.
- **Lexical retrieval misses paraphrased recalls.** Accepted limitation of the slice;
  embeddings come in a later phase. Handle-based recall is always exact.

---

## 15. What comes after the slice (not now)

Multi-provider adapters → ensemble curator → embeddings/vector retrieval → MCP adapter for
Claude Code → transparent `wrap()` → full eval harness. Each is its own spec → plan →
implementation cycle, built on these provider-agnostic interfaces.
