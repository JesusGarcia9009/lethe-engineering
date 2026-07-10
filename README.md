# LETHE

<!-- mcp-name: io.github.JesusGarcia9009/lethe -->

**Live Ephemeral Token & History Engine** — offload big tool outputs out of your LLM agent's
context and recall them on demand, so long tasks cost fewer tokens.

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

LETHE ships as an **MCP server**. Two lines and your agent can move big outputs out of its
context and recall them on demand — fewer tokens on every long task. / LETHE viene como
**servidor MCP**. Dos líneas y tu agente saca outputs grandes del contexto y los recupera cuando
los necesita — menos tokens en cada tarea larga.

**Claude Code:**
```bash
pip install "lethe-llm-context[mcp]"
claude mcp add lethe -- lethe-mcp
```

**Codex:** add an MCP block to `~/.codex/config.toml` — see
[`integrations/codex/mcp-config.md`](integrations/codex/mcp-config.md).

Then drop in the guiding skill so the agent archives **on its own**:
[`integrations/claude-code/SKILL.md`](integrations/claude-code/SKILL.md).

Tools exposed: `lethe_archive` · `lethe_recall` · `lethe_status`.
Full guide: [`integrations/claude-code/mcp-config.md`](integrations/claude-code/mcp-config.md).

---

## ▶️ See it work (no API key) / Míralo funcionar (sin API key)

```bash
python -m lethe.examples.mcp_demo
```

```text
  LETHE — offload big tool outputs, recall on demand, save tokens

The agent runs 4 commands. Each returns a wall of text:

  → build.log               857 tok in context  —archive→  stub '[paged: build.log | handle=6d48a1c2]'
  → pytest.txt              479 tok in context  —archive→  stub '[paged: pytest.txt | handle=1e56b0f4]'
  → db_dump.json            829 tok in context  —archive→  stub '[paged: db_dump.json | handle=ec02...]'
  → trace.txt               414 tok in context  —archive→  stub '[paged: trace.txt | handle=d888...]'

lethe_status:  4 blocks archived, 2579 tokens moved out of context

30 steps later the agent needs a buried fact. It recalls by keyword:

  lethe_recall("launch_code")  →  found launch_code = 4242 (rehydrated losslessly from the archive)

  Context window cost
    without LETHE :  2579 tok  (everything stays resident)
    with LETHE    :    38 tok  (only tiny stubs remain)
    saved         :  2541 tok  (-99%)
```

This runs the **same logic the MCP tools use** — `lethe_archive` / `lethe_recall` / `lethe_status`.

---

## English

### What LETHE is (today, honestly)

When an LLM agent runs a long task (tens to hundreds of steps), its context window fills with
material that *was* useful but no longer is: stale tool outputs, files read 30 steps ago, big
JSON dumps. That means **more tokens per turn**, **higher cost**, and eventually the **context
ceiling**.

LETHE gives the agent an **external, lossless scratch store** so that heavy content lives
*outside* the context window and only a tiny handle stays inside. Two ways to use it:

**1. As an MCP server (the install path above).** The agent calls `lethe_archive(content)` on a
big output and keeps only the returned 4–8-char handle; later it calls `lethe_recall(handle)` or
`lethe_recall("keywords")` to bring the full text back. Nothing is ever deleted — recall is
lossless. The [guiding skill](integrations/claude-code/SKILL.md) tells the agent *when* to do
this, so it happens near-automatically. This is provider-agnostic: it works in any MCP host
(Claude Code, Codex).

**2. As a Python library (in-loop context GC).** `ContextManager` runs an automatic pass inside
your agent loop: a heuristic **Curator** scores each block (recency, whether later blocks cite
it, block kind, plus an optional cheap-model relevance call) and an **Archivist** pages the
coldest blocks out to a store — losslessly, leaving stubs — to hold the working set under a token
budget. Referenced handles are paged back in on demand.

> **Be clear about the mechanism.** An MCP server *cannot* silently rewrite the host's context
> window. LETHE works by giving the agent explicit offload/recall tools plus a skill that makes
> using them near-automatic — not by magic. That honesty is the point.

### ✅ What works today vs. 🗺️ what's on the roadmap

The multi-provider, ensemble, and semantic-retrieval design below is the **long-term vision**,
not what's implemented. Here is the honest split:

| Capability | Status |
|---|---|
| MCP server: `archive` / `recall` / `status`, lossless | ✅ works, shipped |
| Guiding skill for near-automatic offload | ✅ works, shipped |
| Python library: heuristic Curator + budget eviction + lossless paging | ✅ works, tested |
| Needle-in-haystack proof (working set held under budget, fact recovered) | ✅ `1721→199 tok`, ~88% ↓ |
| Optional cheap-model relevance scoring in the Curator | ✅ works (Claude / any adapter) |
| Recall search | 🟡 **lexical/keyword** (SQLite FTS5), not semantic yet |
| **Compactor** (summarize cold runs into dense notes) | 🟡 in the codebase, **not yet wired** into the auto loop |
| Providers | 🟡 **Claude** + a test adapter today; GPT/Gemini/Llama designed, not built |
| Ensemble curation (multi-model voting) | 🗺️ vision, not started |
| Embedding / semantic retrieval | 🗺️ vision, not started |
| One-line `wrap()` drop-in | 🗺️ vision, not started |
| Full eval harness (LoCoMo, ablations, latency) | 🗺️ only the needle eval exists |

Each milestone ships as a tagged release — full notes in [`CHANGELOG.md`](CHANGELOG.md).

### The mental model (OS analogy)

LETHE is designed like an operating system managing virtual memory. This analogy guides the
architecture; the ✅/🟡 above says how much of it runs automatically today.

| Operating system | LETHE |
|---|---|
| Physical RAM | The context window (working set) |
| Disk | External store (SQLite / in-memory) |
| Page-table entry | Stub / handle left in context |
| Page-in on fault | Rehydrating an evicted block |
| Eviction policy | **Curator** (relevance scoring) — ✅ heuristic today |
| Cold-page compression | **Compactor** (consolidation notes) — 🟡 not yet wired |
| Wired / non-swappable memory | Pinned blocks |

### How LETHE differs from agent-memory libraries

Mem0, Zep, Letta and friends persist facts *across sessions*. LETHE targets the opposite:
managing the **live, in-session working context** of a running loop — deciding what to keep in
the window right now. It's complementary to a long-term memory product, not a competitor.
Whether that difference is decisive is something the roadmap above still has to prove.

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

### Design docs

- `docs/specs/2026-06-12-lethe-vertical-slice-design.md` — approved design of the built slice
- `docs/LETHE_engineering_design.md` — the full long-term engineering vision (multi-provider,
  ensemble, embeddings). Read it as **the roadmap**, not the current state.

### License

Released into the public domain under the [Unlicense](LICENSE). Free for everyone, anywhere.

---

## Español

### Qué es LETHE (hoy, con honestidad)

Cuando un agente LLM ejecuta una tarea larga (decenas o cientos de pasos), su ventana de contexto
se llena de material que *fue* útil pero ya no lo es: resultados de herramientas obsoletos,
archivos leídos hace 30 pasos, dumps de JSON enormes. Eso significa **más tokens por turno**,
**más costo** y, al final, el **techo de contexto**.

LETHE le da al agente un **almacén externo y sin pérdida** para que el contenido pesado viva
*fuera* de la ventana de contexto y dentro solo quede un handle diminuto. Dos formas de usarlo:

**1. Como servidor MCP (la instalación de arriba).** El agente llama `lethe_archive(content)`
sobre un output grande y conserva solo el handle de 4–8 caracteres; después llama
`lethe_recall(handle)` o `lethe_recall("palabras")` para traer el texto completo. Nada se borra
nunca — el recall es sin pérdida. El [skill guía](integrations/claude-code/SKILL.md) le dice al
agente *cuándo* hacerlo, así que ocurre casi-automáticamente. Es agnóstico al proveedor: funciona
en cualquier host MCP (Claude Code, Codex).

**2. Como librería Python (GC de contexto dentro del loop).** `ContextManager` corre una pasada
automática dentro de tu loop: un **Curator** heurístico puntúa cada bloque (recencia, si bloques
posteriores lo citan, tipo de bloque, más una llamada opcional a un modelo barato) y un
**Archivist** pagina los bloques más fríos a un almacén — sin pérdida, dejando stubs — para
mantener el working set bajo un presupuesto de tokens. Los handles referenciados se repaginan
bajo demanda.

> **Seamos claros con el mecanismo.** Un servidor MCP *no puede* reescribir en silencio la
> ventana de contexto del host. LETHE funciona dándole al agente tools explícitas de
> offload/recall más un skill que hace que usarlas sea casi automático — no por magia. Esa
> honestidad es el punto.

### ✅ Qué funciona hoy vs. 🗺️ qué está en el roadmap

El diseño multi-proveedor, ensamble y retrieval semántico de abajo es la **visión a largo
plazo**, no lo implementado. La división honesta:

| Capacidad | Estado |
|---|---|
| Servidor MCP: `archive` / `recall` / `status`, sin pérdida | ✅ funciona, publicado |
| Skill guía para offload casi-automático | ✅ funciona, publicado |
| Librería: Curator heurístico + expulsión por presupuesto + paginación sin pérdida | ✅ funciona, con tests |
| Prueba aguja-en-pajar (working set bajo presupuesto, dato recuperado) | ✅ `1721→199 tok`, ~88% ↓ |
| Scoring opcional con modelo barato en el Curator | ✅ funciona (Claude / cualquier adapter) |
| Búsqueda de recall | 🟡 **léxica/keyword** (SQLite FTS5), aún no semántica |
| **Compactor** (resumir runs frías en notas densas) | 🟡 está en el código, **aún no conectado** al loop |
| Proveedores | 🟡 **Claude** + un adapter de prueba hoy; GPT/Gemini/Llama diseñados, no construidos |
| Curación por ensamble (voto multi-modelo) | 🗺️ visión, sin empezar |
| Retrieval por embeddings / semántico | 🗺️ visión, sin empezar |
| Drop-in `wrap()` de una línea | 🗺️ visión, sin empezar |
| Harness de eval completo (LoCoMo, ablations, latencia) | 🗺️ solo existe el needle eval |

Cada milestone se publica como release etiquetada — notas completas en [`CHANGELOG.md`](CHANGELOG.md).

### El modelo mental (analogía con el SO)

LETHE se diseña como un sistema operativo que gestiona memoria virtual. La analogía guía la
arquitectura; el ✅/🟡 de arriba dice cuánto de eso corre automáticamente hoy.

| Sistema operativo | LETHE |
|---|---|
| Memoria RAM | La ventana de contexto (working set) |
| Disco | Almacén externo (SQLite / en memoria) |
| Entrada de tabla de páginas | Stub / handle que queda en contexto |
| Traer página al fallar | Rehidratar un bloque expulsado |
| Política de expulsión | **Curator** (puntúa relevancia) — ✅ heurístico hoy |
| Compresión de páginas frías | **Compactor** (notas de consolidación) — 🟡 aún no conectado |
| Memoria fija / no intercambiable | Bloques fijados (pinned) |

### En qué se diferencia de las librerías de memoria de agentes

Mem0, Zep, Letta y compañía persisten hechos *entre sesiones*. LETHE apunta a lo contrario:
gestionar el **contexto vivo de la sesión** de un loop en marcha — decidir qué mantener en la
ventana ahora mismo. Es complementario a un producto de memoria a largo plazo, no un competidor.
Si esa diferencia es decisiva es algo que el roadmap de arriba todavía debe demostrar.

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

### Documentos de diseño

- `docs/specs/2026-06-12-lethe-vertical-slice-design.md` — diseño aprobado del corte construido
- `docs/LETHE_engineering_design.md` — la visión de ingeniería completa a largo plazo
  (multi-proveedor, ensamble, embeddings). Léelo como **el roadmap**, no como el estado actual.

### Licencia

Liberado al dominio público bajo la [Unlicense](LICENSE). Libre para todos, en cualquier lugar.
