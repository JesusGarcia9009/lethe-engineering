# LETHE

**Live Ephemeral Token & History Engine** — a model-agnostic context garbage collector for long-running LLM agents.

> 🌍 This README is bilingual. [English](#english) · [Español](#español)

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

### Status

This repository is being built as a **vertical slice first**: the full block lifecycle
working end-to-end with a single provider (Claude), proven by a needle-in-haystack test,
before adding multi-provider, ensemble curation, embeddings, and the MCP adapter.

See the design and plan:
- `docs/specs/2026-06-12-lethe-vertical-slice-design.md` — approved design
- `docs/plans/2026-06-12-lethe-vertical-slice.md` — task-by-task implementation plan
- `docs/LETHE_engineering_design.md` — the full long-term engineering design

### Quickstart (no API key needed)

```bash
python -m pytest -q          # run the full test suite, including the needle test
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
python -m pytest -q          # corre toda la suite de tests, incluida la prueba de la aguja
```

### Demo con Claude real

```powershell
$env:ANTHROPIC_API_KEY="sk-..."   # PowerShell
python -m lethe.examples.claude_loop
```

### Licencia

Liberado al dominio público bajo la [Unlicense](LICENSE). Libre para todos, en cualquier lugar.
