# LETHE

<!-- mcp-name: io.github.JesusGarcia9009/lethe -->

**Live Ephemeral Token & History Engine** — a model-agnostic context garbage collector for long-running LLM agents.

[![PyPI](https://img.shields.io/pypi/v/lethe-llm-context?color=blue)](https://pypi.org/project/lethe-llm-context/)
[![Python](https://img.shields.io/pypi/pyversions/lethe-llm-context)](https://pypi.org/project/lethe-llm-context/)
[![MCP Registry](https://img.shields.io/badge/MCP_Registry-listed-1f6feb)](https://registry.modelcontextprotocol.io)
[![License: Unlicense](https://img.shields.io/badge/license-Unlicense-green)](LICENSE)

> 🌍 This README is bilingual. [English](#english) · [Español](#español)

<p align="center">
  <img src="assets/lethe-demo.gif" alt="LETHE archives big tool outputs and recalls them on demand to save tokens" width="820">
</p>

---

## 🔌 Use it in Claude Code or Codex (save tokens now)

LETHE ships as an **MCP server**. Two lines and your agent can offload big outputs out of its
context and recall them on demand — fewer tokens on every long task. / LETHE viene como
**servidor MCP**. Dos líneas y tu agente descarga outputs grandes fuera del contexto y los
recupera cuando los necesita — menos tokens en cada tarea larga.

**Claude Code:**
```bash
pip install "lethe-llm-context[mcp]"
claude mcp add lethe -- lethe-mcp
```

**Codex:** add an MCP block to `~/.codex/config.toml` — see
[`integrations/codex/mcp-config.md`](integrations/codex/mcp-config.md).

Then drop in the guiding skill so it happens **automatically**:
[`integrations/claude-code/SKILL.md`](integrations/claude-code/SKILL.md).

Tools exposed: `lethe_archive` · `lethe_recall` · `lethe_status`.
Full guide: [`integrations/claude-code/mcp-config.md`](integrations/claude-code/mcp-config.md).

---

## ▶️ See it work (no API key) / Míralo funcionar (sin API key)

```bash
python -m lethe.examples.mcp_demo
```

```text
  LETHE — context garbage collector for LLM agents
  archive big tool outputs · recall on demand · save tokens

The agent runs 4 commands. Each returns a wall of text:

  → build.log               857 tok in context  —archive→  stub '[paged: build.log | handle=6d48]'  handle=6d48
  → pytest.txt              479 tok in context  —archive→  stub '[paged: pytest.txt | handle=1e56]'  handle=1e56
  → db_dump.json            829 tok in context  —archive→  stub '[paged: db_dump.json | handle=ec02]'  handle=ec02
  → trace.txt               414 tok in context  —archive→  stub '[paged: trace.txt | handle=d888]'  handle=d888

lethe_status:  4 blocks archived, 2579 tokens moved out of context

30 steps later the agent needs a buried fact. It recalls by keyword:

  lethe_recall("launch_code")  →  found launch_code = 4242 (rehydrated losslessly from the archive)

  Context window cost

    without LETHE :  2579 tok  (everything stays resident)
    with LETHE    :    34 tok  (only tiny stubs remain)
    saved         :  2545 tok  (-99%)
```

This runs the **same logic the MCP tools use** — `lethe_archive` / `lethe_recall` / `lethe_status`.
Regenerate the GIF at the top with `python assets/make_gif.py` (self-contained, Pillow only); a
[`assets/demo.tape`](assets/demo.tape) is also provided for [VHS](https://github.com/charmbracelet/vhs)
on Linux/WSL. / El GIF de arriba se regenera con `python assets/make_gif.py` (solo Pillow).

---

## English

When an LLM agent runs a long task (tens to hundreds of steps), its context window fills
with material that *was* useful but no longer is: stale tool outputs, files read 30 steps
ago, dead reasoning branches. This causes three failures: **quality decay** (relevant
tokens buried under noise), **cost growth** (every turn re-sends the bloated history), and
**hard limits** (the agent eventually hits the context ceiling and breaks).

LETHE sits inside the agent loop and manages the live context like an operating system
manages virtual memory. A multi-agent core scores each context block's relevance to the
current goal, compacts finished work into dense notes, and pages cold material to an
external store — **losslessly**, so anything can be recalled on demand.

### The mental model (OS analogy)

| Operating system | LETHE |
|---|---|
| Physical RAM | The context window (working set) |
| Disk | External store (SQLite) |
| Page-table entry | Stub / handle left in context |
| Page-in on fault | Rehydrating an evicted block |
| Eviction policy | **Curator** (relevance scoring) |
| Cold-page compression | **Compactor** (consolidation notes) |
| Wired / non-swappable memory | Pinned blocks |

### The three workers

- **Curator** — scores each block `0..1` for relevance to the current goal (heuristics + a cheap model).
- **Compactor** — replaces runs of finished steps with one dense summary note.
- **Archivist** — pages cold blocks to the store and brings them back on demand.

A **Scheduler** orchestrates them on triggers (every K steps, or when over budget).

### Status & progress / Estado y progreso

This repository is being built as a **vertical slice first**: the full block lifecycle
working end-to-end with a single provider (Claude), proven by a needle-in-haystack test,
before adding multi-provider, ensemble curation, embeddings, and the MCP adapter.

Each milestone ships as a tagged release. Full notes in [`CHANGELOG.md`](CHANGELOG.md).

| Version | Milestone | What it does / Qué hace | Status |
|---|---|---|---|
| `v0.1.0` | A — Foundation | Core types, fake adapter, stores — the testable bedrock | ✅ |
| `v0.2.0` | B — Heuristic Engine | Curator + Scheduler + Manager: score & evict under budget | ✅ |
| `v0.3.0` | C — Compactor | Summarize finished runs into dense notes | ✅ |
| `v0.4.0` | D — Archivist & Paging | Lossless paging + recall + needle test (**1721→197 tok, ~89% ↓**) | ✅ |
| `v0.5.0` | E — Visualizer + Claude | Live console view + real Claude adapter + runnable demos | ✅ |
| `v0.6.0` | MCP server | `lethe_archive`/`recall`/`status` for Claude Code + Codex, plus guiding skill | ✅ |

🎉 **Vertical slice complete and shipping via MCP.** Next: PyPI + MCP registry publish, then multi-provider, ensemble, and embeddings — each its own spec → plan → release cycle.

See the design and plan:
- `docs/specs/2026-06-12-lethe-vertical-slice-design.md` — approved design
- `docs/plans/2026-06-12-lethe-vertical-slice.md` — task-by-task implementation plan
- `docs/LETHE_engineering_design.md` — the full long-term engineering design

### Quickstart (no API key needed)

```bash
python -m pytest -q                  # run the full test suite, including the needle test
python -m lethe.examples.fake_loop   # WATCH it work: live view, blocks paging out, budget held
```

### Real Claude demo

```powershell
$env:ANTHROPIC_API_KEY="sk-..."   # PowerShell
python -m lethe.examples.claude_loop
```

### License

Released into the public domain under the [Unlicense](LICENSE). Free for everyone, anywhere.

---

## Español

Cuando un agente LLM ejecuta una tarea larga (decenas o cientos de pasos), su ventana de
contexto se llena de material que *fue* útil pero ya no lo es: resultados de herramientas
obsoletos, archivos leídos hace 30 pasos, ramas de razonamiento muertas. Esto provoca tres
fallos: **pérdida de calidad** (lo relevante queda enterrado entre ruido), **aumento de
costo** (cada turno reenvía todo el historial inflado) y **límites duros** (el agente acaba
chocando con el techo de contexto y se rompe).

LETHE vive dentro del bucle del agente y gestiona el contexto vivo como un sistema operativo
gestiona la memoria virtual. Un núcleo multi-agente puntúa la relevancia de cada bloque
respecto al objetivo actual, compacta el trabajo terminado en notas densas, y pagina el
material frío a un almacén externo — **sin pérdida**, de modo que todo se puede recuperar
cuando haga falta.

### El modelo mental (analogía con el SO)

| Sistema operativo | LETHE |
|---|---|
| Memoria RAM | La ventana de contexto (working set) |
| Disco | Almacén externo (SQLite) |
| Entrada de tabla de páginas | Stub / handle que queda en contexto |
| Traer página al fallar | Rehidratar un bloque expulsado |
| Política de expulsión | **Curator** (puntúa relevancia) |
| Compresión de páginas frías | **Compactor** (notas de consolidación) |
| Memoria fija / no intercambiable | Bloques fijados (pinned) |

### Los tres trabajadores

- **Curator** — puntúa cada bloque `0..1` según su relevancia al objetivo actual (heurísticas + un modelo barato).
- **Compactor** — reemplaza secuencias de pasos terminados por una nota-resumen densa.
- **Archivist** — pagina los bloques fríos al almacén y los recupera cuando se necesitan.

Un **Scheduler** los coordina mediante disparadores (cada K pasos, o al exceder el presupuesto).

### Estado

Este repositorio se construye **primero como un corte vertical**: el ciclo de vida completo
de un bloque funcionando de punta a punta con un solo proveedor (Claude), demostrado por una
prueba de "aguja en el pajar", antes de añadir multi-proveedor, curación por ensamble,
embeddings y el adaptador MCP.

Consulta el diseño y el plan:
- `docs/specs/2026-06-12-lethe-vertical-slice-design.md` — diseño aprobado
- `docs/plans/2026-06-12-lethe-vertical-slice.md` — plan de implementación tarea por tarea
- `docs/LETHE_engineering_design.md` — el diseño de ingeniería completo a largo plazo

### Inicio rápido (sin API key)

```bash
python -m pytest -q                  # corre toda la suite, incluida la prueba de la aguja
python -m lethe.examples.fake_loop   # VELO funcionar: vista en vivo, bloques paginándose, presupuesto sostenido
```

### Demo con Claude real

```powershell
$env:ANTHROPIC_API_KEY="sk-..."   # PowerShell
python -m lethe.examples.claude_loop
```

### Licencia

Liberado al dominio público bajo la [Unlicense](LICENSE). Libre para todos, en cualquier lugar.
