# LETHE — Roadmap & honest status

This file is the single source of truth for **what LETHE actually does today vs. what the full
engineering design (`docs/LETHE_engineering_design.md`) still promises**. The README's status
table is the short version; this is the detailed record. Keep it honest — update it as things
ship.

Last updated: 2026-07-10.

---

## Part 1 — Vertical slice (`docs/specs/2026-06-12-lethe-vertical-slice-design.md`)

**Status: COMPLETE (100%).** This is the spec LETHE actually committed to build. Its acceptance
criteria (§13) all pass, and — importantly — the two long-standing gaps against its *architecture*
were closed on 2026-07-10:

- The **Compactor is now wired into the GC loop** (§8 "score → decide → compact → page"). Until
  then it was dead code and the `COMPACTED` state never happened automatically. The needle eval
  now shows real compaction (`compacted: 2, notes: 1`).
- **`never_compact_open_subgoal`** (§7.2, §8 safety) is implemented: `Scheduler.cold_run` never
  compacts blocks of the still-open subgoal and never lets a run span a subgoal boundary;
  `Session.set_subgoal()` advances the active subgoal.
- The **`refs` citation graph** (§6 SQL) is now created and populated in `SqliteStore`
  (`refs_of(src)` reads it back).

Nothing outstanding against the vertical slice.

---

## Part 2 — Full engineering design (`docs/LETHE_engineering_design.md`)

**Status: ~45–50%.** This is the long-term vision. The remainder is deliberately *not* built yet
— shipping something honest and working beat chasing a 6–12-month scope solo. This section is the
record of what's left.

### Goals G1–G5

| Goal | Target | Today | Gap to close |
|---|---|---|---|
| **G1** Provider-agnostic | Claude, GPT, Gemini, Llama, Hermes via one PAL | Claude (`AnthropicAdapter`) + `FakeAdapter` only | Build `openai.py`, `gemini.py`, `openai_compatible.py` (Llama/Hermes), `tokenizers.py` registry. The `ProviderAdapter` protocol is reduced to `complete` + `token_counter`; restore `to_native`/`embed` if needed. |
| **G2** Multi-agent core | Curator + Compactor + Archivist, plus **ensemble** voting | All three workers real and wired ✅ · ensemble ❌ | Add multi-model Curator: poll N cheap models, aggregate (trimmed-mean), uncertainty-bias toward keep. |
| **G3** Lossless-by-default | Nothing destroyed; recall on demand | ✅ done | — |
| **G4** Drop-in | One-line `wrap()` + MCP adapter | MCP ✅ (on registry) · `wrap()` ❌ | Implement `lethe.wrap(agent)` middleware that runs the GC pass before each `complete()`. |
| **G5** Measurable | Eval harness: token reduction, task-success retention, wrong-eviction rate, net savings, latency | Only the needle eval | Build `evals/harness.py` + `report.py`; add LoCoMo / long-horizon agent tasks; ablations (heuristic vs single-model vs ensemble). |

### 7-phase roadmap (§14 of the design doc)

| Phase | What | Status |
|---|---|---|
| 0 — Scaffolding & PAL (5 adapters, exact token counts) | ❌ superseded by the single-provider vertical slice |
| 1 — Manager + heuristic policy | ✅ |
| 2 — Curator (single model) + Compactor | ✅ (Compactor wired 2026-07-10) |
| 3 — Archivist + paging store | ✅ lexical (FTS5); 🟡 no vector/semantic retrieval |
| 4 — Ensemble Curator | ❌ |
| 5 — MCP adapter | ✅ (v0.6.x, on the official registry) |
| 6 — Eval harness | 🟡 needle only |
| 7 — Transparent `wrap()`, docs, polish | 🟡 docs/examples ✅, `wrap()` ❌ |

### Other known gaps / debt

- **Retrieval is lexical, not semantic.** `store.search` uses SQLite FTS5 / substring. No
  embeddings, no `sqlite-vss` vector table (design §11). Paraphrased recalls can miss; handle
  recall is always exact.
- **Curator cost at scale.** With a real cheap-model curator, scoring runs per block per trigger.
  Mitigated (heuristic-first, single scoring pass per `_gc` iteration, compaction only under
  budget pressure) but there's no score cache across triggers yet.
- **SQLite concurrency.** Single shared connection (`check_same_thread=False`); fine for local
  single-user MCP, not for thousands of concurrent sessions. No pooling, no `handle` index.
- **MCP data isolation.** The MCP server uses one process-wide `LetheMemory(session="default")`;
  all clients share one archive namespace. Fine locally, a gap for multi-tenant use.
- **No schema migration/versioning** in `SqliteStore` — the first schema change breaks existing
  user DBs.
- **Config is in-code only** — no YAML loader (design §10/§11 marks YAML "optional").

---

## Priority guidance (solo, part-time)

Distribution/adoption beats new features right now (see `docs/promotion/`). On the code side, the
highest-leverage next steps, in order:

1. **A second real provider** (OpenAI-compatible / Ollama) — the "cheap local curator" cost play,
   the most-requested capability. **Not** the full 5-provider matrix, **not** the ensemble.
2. **Semantic recall** (embeddings) — the biggest quality win for `recall`.
3. **`wrap()` drop-in** — lowers integration friction for library users.

Everything else (ensemble, full harness, multi-tenant MCP) waits for real users asking for it.
