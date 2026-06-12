# Changelog

All notable changes to LETHE are documented here.
Todos los cambios relevantes de LETHE se documentan aquí.

Format based on [Keep a Changelog](https://keepachangelog.com/) ·
Versioning follows [Semantic Versioning](https://semver.org/).

The project is being built as a **vertical slice**: each milestone is a shippable,
test-backed release. / El proyecto se construye como **corte vertical**: cada milestone es
una release con tests.

---

## [Unreleased]

_Next: publish to PyPI + the MCP registry, then multi-provider, ensemble curator, embeddings._
_Próximo: publicar en PyPI + el MCP registry, luego multi-proveedor, ensamble, embeddings._

---

## [0.6.0] — MCP Server / Servidor MCP — 2026-06-12

> **EN:** LETHE now ships to where people work. An MCP server lets Claude Code and Codex
> offload large tool outputs out of context and recall them on demand — real token savings,
> two-line install. **ES:** LETHE ahora llega a donde la gente trabaja. Un servidor MCP
> permite a Claude Code y Codex descargar outputs grandes fuera del contexto y recuperarlos
> cuando hagan falta — ahorro real de tokens, instalación en dos líneas.

### Added / Añadido
- `lethe/mcp/service.py` — `LetheMemory`: pure, tested offload service (`archive`, `recall`,
  `status`) reusing `SqliteStore` + `Archivist`. No MCP dependency, so it is fully unit-tested.
- `lethe/mcp/server.py` — thin **FastMCP** (stdio) server exposing `lethe_archive`,
  `lethe_recall`, `lethe_status`. Verified to start and serve all three tools.
- `integrations/claude-code/SKILL.md` — guiding skill so the agent offloads large outputs
  (> ~1500 tokens) automatically.
- Two-line install snippets for **Claude Code** and **Codex**
  (`integrations/*/mcp-config.md`), plus a prominent README install section.
- Optional `[mcp]` dependency extra.

### Honest scope / Alcance honesto
- MCP cannot rewrite the host's context; LETHE offers explicit offload/recall tools and a
  skill that makes their use near-automatic. / MCP no puede reescribir el contexto del host;
  LETHE ofrece herramientas explícitas de offload/recall y una skill que las usa casi
  automáticamente.

---

## [0.5.0] — Milestone E: Visualizer & Real Claude / Visualizador y Claude Real — 2026-06-12

> **EN:** You can now see it work and run it for real. A read-only live console view shows
> blocks paging out and the budget bar holding, plus the real Anthropic adapter. **ES:** Ya
> se puede ver funcionar y correr de verdad. Una vista en vivo (solo lectura) muestra los
> bloques paginándose y la barra de presupuesto sostenida, más el adaptador real de Anthropic.

### Added / Añadido
- `viz/console.py`: `render_frame` — live working-set view with state tags
  (`ACTIVE`/`WARM`/`NOTE`/`[paged]`/`PIN`) and a budget bar (ASCII-safe for Windows).
- `AnthropicAdapter`: real Claude via the `anthropic` SDK, with cached per-text token
  counting and an offline fallback. Imports without the SDK installed.
- `examples/fake_loop.py`: a runnable **no-API-key** demo that prints the live view each step.
- `examples/claude_loop.py`: the same loop against real Claude.

### Marks the completion of the vertical slice. / Marca el fin del corte vertical.

---

## [0.4.0] — Milestone D: Archivist & Paging / Archivista y Paginación — 2026-06-12

> **EN:** The lossless paging layer, and the proof it works. Cold blocks are written to an
> external store and replaced in context by a one-line stub; anything can be recalled later
> by handle or by lexical search. **ES:** La capa de paginación sin pérdida, y la prueba de
> que funciona. Los bloques fríos se guardan en un almacén externo y se reemplazan en
> contexto por un stub de una línea; todo se puede recuperar después por handle o por
> búsqueda léxica.

### Added / Añadido
- `SqliteStore` with SQLite **FTS5** lexical search (source of truth on disk).
- `Archivist`: `page_out` (write + stub), `page_fault` (restore by handle), `recall`
  (lexical search).
- `ContextManager`: paging stubs in the working set, `observe()` to rehydrate blocks the
  model references by handle, `recall()`, and **honest token accounting** (each real block
  counted once at full size; stubs excluded from the savings metric).
- Bounded GC loop that converges under budget by dropping stale stubs.
- 🪡 **Needle-in-haystack eval** (`lethe.evals.needle`): the value proof. Plant a fact, bury
  it under 49 noisy steps, recall it under budget.

### Proven / Demostrado
- Needle recovered after 45 evictions. Tokens: **1721 → 197 (~89% reduction)**, working set
  ≤ budget (200) the entire run.

---

## [0.3.0] — Milestone C: Compactor / Compactador — 2026-06-12

> **EN:** Finished work gets summarized. A contiguous run of completed cold blocks is
> replaced by one dense consolidation note. **ES:** El trabajo terminado se resume. Una
> secuencia de bloques fríos completados se reemplaza por una nota de consolidación densa.

### Added / Añadido
- `Compactor` producing consolidation notes with guardrails: never compacts pinned blocks,
  and skips compaction that would not actually save tokens (no negative-savings notes).

---

## [0.2.0] — Milestone B: Heuristic Engine / Motor Heurístico — 2026-06-12

> **EN:** The brain that decides what to keep. Scores every block's relevance and evicts the
> least useful to stay under a token budget. **ES:** El cerebro que decide qué conservar.
> Puntúa la relevancia de cada bloque y expulsa los menos útiles para no pasar el
> presupuesto de tokens.

### Added / Añadido
- `Curator`: heuristic relevance scoring (recency, reference count, kind weight, pins)
  blended with an optional cheap-model judgment.
- `Scheduler`: deterministic budget eviction protecting pinned blocks and the most recent
  steps.
- `ContextManager`: sessions, automatic GC on triggers, `render()`, `pin`/`unpin`, and
  `stats()` reporting token savings.

---

## [0.1.0] — Milestone A: Foundation / Fundación — 2026-06-12

> **EN:** The provider-agnostic bedrock that lets everything else be built and tested with
> no network. **ES:** La base agnóstica de proveedor que permite construir y testear todo lo
> demás sin red.

### Added / Añadido
- Package scaffold and `pyproject.toml`.
- Core types: `Block`, `Message`, `BlockState` (the block lifecycle).
- `ProviderAdapter` / `TokenCounter` / `Response` interfaces.
- `FakeAdapter` + `FakeTokenCounter` — deterministic, no network, enabling TDD.
- `Store` interface, `MemoryStore` with lexical search, and the `Note` type.
- Approved design spec and task-by-task implementation plan under `docs/`.

[Unreleased]: https://github.com/JesusGarcia9009/lethe-engineering/compare/v0.6.0...HEAD
[0.6.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.6.0
[0.5.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.5.0
[0.4.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.4.0
[0.3.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.3.0
[0.2.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.2.0
[0.1.0]: https://github.com/JesusGarcia9009/lethe-engineering/releases/tag/v0.1.0
