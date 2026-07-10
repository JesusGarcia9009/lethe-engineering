# LETHE Compactor-in-the-Loop — Design Spec (Phase 2)

> Status: approved · Target builder: Claude Code · Date: 2026-07-10
> Parent: `2026-06-12-lethe-vertical-slice-design.md` · Builds on released v0.6.2
> Fixes review finding **C2**: the Compactor exists but is never called by the GC loop,
> so the `COMPACTED` state in the block lifecycle never happens automatically.

---

## 1. Purpose

Make the `Compactor` a real part of the automatic context-GC loop. Today `Session._gc()` only
pages cold blocks out as one-line stubs; `lethe/agents/compactor.py` is dead code referenced
only by its own tests. This spec wires compaction in so that a contiguous run of cold, completed
blocks is replaced by **one dense consolidation note** that stays resident, while the originals
are paged out **losslessly** — turning `ACTIVE → WARM → COMPACTED → PAGED` into observable
behavior and giving LETHE a real differentiator over a plain key-value offload store.

## 2. Trigger policy (decided)

Compaction fires **only under budget pressure** — inside `_gc()`, when the working set exceeds
the token budget, *before* falling back to paging. Rationale: each compaction is one model call;
gating it behind budget pressure bounds the cost (addresses the review's "Curator/Compactor cost
could eat the savings" risk) and turns N would-be stubs into one useful note. Rejected
alternatives: opportunistic every-K-steps (makes calls with no budget need) and manual-only
(doesn't make `COMPACTED` automatic, so C2 stays open).

## 3. Control flow

`Session._gc()`, per iteration (the existing 50-iteration bound is preserved):

```
if token_count(working_set) <= target:      break          # already fits
scores = scheduler.score(blocks, step, goal)               # ONE scoring pass
run    = scheduler.cold_run(blocks, step, goal, scores)    # longest cold contiguous run
if len(run) >= 2 and _try_compact(run):     continue       # compacted; recount next loop
kept, evicted = scheduler.plan(blocks, step, goal, scores) # else page coldest as stub
if not evicted:                             break
<page out evicted as stubs — existing logic>
```

A "cold contiguous run" = the longest maximal run, in working-set order, of blocks that are all:
not pinned, not in the protected last-`keep_last_n_steps`, score `< thresholds.cold`, and not
themselves a note or a stub.

**One scoring pass:** `plan()` and `cold_run()` both accept an optional precomputed `scores=`
dict so `_gc()` scores once per iteration and never doubles model calls when a real cheap-model
curator is configured.

## 4. Component changes (small, isolated units)

### 4.1 `Scheduler` (`lethe/core/scheduler.py`)
- `score(blocks, now_step, goal) -> dict[str,float]` — public passthrough to the curator.
- `plan(..., scores=None)` and new `cold_run(..., scores=None)` — reuse `scores` if given,
  else compute. Extract the existing protected-steps logic into a shared helper.
- `cold_run` returns the longest compactable contiguous run (or `[]`).

### 4.2 `Archivist` (`lethe/agents/archivist.py`)
- `compact_out(block) -> str` — assign a unique handle (via `_fresh_handle`), set
  `state = COMPACTED`, `store.put(block)`, emit a `compact_out` event, return the handle.
  Unlike `page_out`, it leaves **no stub** in context (the note replaces the whole run).

### 4.3 `Compactor` (`lethe/agents/compactor.py`)
- No interface change. Reused as-is. Guardrails already present: returns `None` on pinned blocks
  or when the note is not smaller than the run (no negative-savings compaction).

### 4.4 `Session` (`lethe/core/manager.py`)
- Construct `self.compactor = Compactor(cm.curator_adapter)` and a stable `self.session_id`.
- `_try_compact(run) -> bool`:
  1. `note = compactor.compact(run, session_id)`; if `None`, return `False`.
  2. `handles = [archivist.compact_out(b) for b in run]`.
  3. Build `note_block` (`kind="note"`, `state=ACTIVE`, `content=note.summary`,
     `tokens=note.tokens`, `meta={"covers": handles, "note_id": note.id}`),
     placed at the run's original position.
  4. `store.put_note(note)`; replace the run with `note_block`, preserving order.
  5. Increment `_compacted` (by len(run)) and `_notes`; return `True`.
- `stats()` gains `compacted` and `notes`. `evicted` now counts **all** blocks removed from the
  working set (paged + compacted), so existing `evicted >= 1` assertions still hold.

## 5. Losslessness & provenance

Originals are never destroyed — `compact_out` writes each to the store with a handle before the
run is replaced. `note_block.meta["covers"]` holds those handles. Recall paths are unaffected:
`recall(handle)` / `recall("keywords")` and `observe()`'s page-fault-on-referenced-handle still
resolve the originals, whether they were paged (stub) or compacted (note).

## 6. Testing

- **New:** compaction-in-loop test with `FakeAdapter(handler=<summarizer>)` asserting: a `note`
  block appears in the rendered working set with the summary text; originals are recovered
  losslessly by keyword and by handle; token savings hold; originals are in state `COMPACTED`.
- **New (scheduler):** `cold_run` returns the expected contiguous run and respects pins /
  protected steps / the cold threshold; returns `[]` when nothing qualifies.
- **Updated:** `test_manager` / `test_needle` assertions adjusted to the new behavior — they keep
  proving *budget held* and *needle recovered losslessly*, which remain true.
- Full suite must stay green; the needle eval must still recover the fact under budget.

### Honest caveat (documented, not a bug)
With a *non-summarizing* test adapter (no handler), `compact()` "summarizes" to `""`, so the
resident note is empty. Losslessness is unaffected (originals are in the store and recall finds
them); only the in-context note carries no text. Real adapters (Claude) produce real summaries —
same split the project already uses: tests prove the mechanism, the Claude demo proves quality.

## 7. Scope

### In scope (this release, → v0.7.0)
- The control-flow, Scheduler, Archivist, and Session changes above; tests; CHANGELOG entry.

### Out of scope (still roadmap)
- Sub-goal boundary tracking (not modeled in `Block` yet) — `never_compact_open_subgoal`.
- Semantic/embedding-based compaction or retrieval.
- Opportunistic every-K-steps compaction (rejected by the trigger decision).
- Exposing compaction through the MCP server (the MCP path stays manual archive/recall for now).

## 8. Acceptance criteria

1. A 10+-step synthetic loop over budget produces at least one `note` block in the working set
   and stays under budget.
2. Blocks folded into a note are recoverable losslessly (keyword and handle) and are in state
   `COMPACTED` in the store.
3. `cold_run` never selects pinned or protected blocks and only selects sub-cold runs.
4. Scoring happens at most once per `_gc` iteration.
5. Full test suite and the needle eval pass.
