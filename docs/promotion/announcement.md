# Announcement drafts / Borradores de anuncio

Copy-paste ready. Headline number: **1721 → 199 tokens (~88% reduction)** from the needle test.

---

## X / Twitter (EN)

> 🧠 Long agent tasks blow up your context window — and your token bill.
>
> I built **LETHE**: a context garbage collector for LLM agents. It offloads big tool
> outputs out of context and recalls them on demand. Losslessly.
>
> In the needle test: **1721 → 199 tokens (~88% ↓)**, fact still recalled.
>
> Works in Claude Code & Codex via MCP, two lines:
> `pip install "lethe-llm-context[mcp]"`
>
> 🔗 github.com/JesusGarcia9009/lethe-engineering
> #LLM #ClaudeCode #MCP #AI

## X / Twitter (ES)

> 🧠 Las tareas largas de un agente inflan tu ventana de contexto — y tu factura de tokens.
>
> Construí **LETHE**: un recolector de basura de contexto para agentes LLM. Descarga los
> outputs grandes fuera del contexto y los recupera cuando hacen falta. Sin pérdida.
>
> En la prueba de la aguja: **1721 → 199 tokens (~88% ↓)**, el dato se recupera igual.
>
> Funciona en Claude Code y Codex vía MCP, dos líneas:
> `pip install "lethe-llm-context[mcp]"`
>
> 🔗 github.com/JesusGarcia9009/lethe-engineering

---

## LinkedIn (EN)

> **Long-running AI agents have a hidden tax: context bloat.**
>
> When an agent runs a task across dozens of steps, its context window fills with stale tool
> outputs and old file reads. The result: higher cost, degraded quality, and eventually a
> hard context limit.
>
> So I built **LETHE** — a context garbage collector for LLM agents, modeled on how an
> operating system manages virtual memory. It scores each block's relevance, summarizes
> finished work, and pages cold material to an external store — **losslessly**, so nothing is
> lost and anything can be recalled on demand.
>
> In a needle-in-a-haystack test, a fact planted at step 0 survived dozens of evictions and was
> recalled 50 steps later — while tokens dropped from **1721 to 199 (~88% reduction)**.
>
> It ships as an MCP server, so it plugs into Claude Code and Codex in two lines, and it's
> open source (public domain) on PyPI.
>
> Install: `pip install "lethe-llm-context[mcp]"`
> Repo: https://github.com/JesusGarcia9009/lethe-engineering
>
> Built in the open. Feedback welcome. #AI #LLM #SoftwareEngineering #MCP #ClaudeCode

## LinkedIn (ES)

> **Los agentes de IA de larga duración tienen un impuesto oculto: el contexto inflado.**
>
> Cuando un agente ejecuta una tarea en decenas de pasos, su ventana de contexto se llena de
> outputs viejos y archivos que ya no importan. Resultado: más costo, peor calidad y, al
> final, un límite duro de contexto.
>
> Por eso construí **LETHE** — un recolector de basura de contexto para agentes LLM, inspirado
> en cómo un sistema operativo gestiona la memoria virtual. Puntúa la relevancia de cada
> bloque, resume el trabajo terminado y pagina el material frío a un almacén externo — **sin
> pérdida**, de modo que nada se pierde y todo se puede recuperar.
>
> En una prueba de "aguja en el pajar", un dato plantado en el paso 0 sobrevivió a decenas de
> expulsiones y se recuperó 50 pasos después — mientras los tokens bajaban de **1721 a 199
> (~88% menos)**.
>
> Viene como servidor MCP: se conecta a Claude Code y Codex en dos líneas, y es open source
> (dominio público) en PyPI.
>
> Instalar: `pip install "lethe-llm-context[mcp]"`
> Repo: https://github.com/JesusGarcia9009/lethe-engineering

---

## Reddit (r/LocalLLaMA, r/ClaudeAI) — EN

**Title:** I built a context garbage collector for LLM agents — ~88% fewer tokens on long tasks (open source, MCP for Claude Code & Codex)

**Body:**

> Long agent loops fill the context window with stale tool outputs and old file reads. That
> costs tokens, hurts quality ("lost in the middle"), and eventually hits the context ceiling.
>
> **LETHE** treats the context like an OS treats virtual memory: it scores each block's
> relevance to the current goal, compacts finished work into dense notes, and pages cold
> material to a SQLite store — losslessly, recallable by handle or keyword search.
>
> In a needle-in-a-haystack test, a fact planted at step 0 was recalled after dozens of evictions,
> with tokens going **1721 → 199 (~88% reduction)** and the working set staying under budget
> the whole run.
>
> It ships as an MCP server, so two lines wire it into Claude Code or Codex:
> ```
> pip install "lethe-llm-context[mcp]"
> claude mcp add lethe -- lethe-mcp
> ```
> A small guiding skill makes the agent offload large outputs automatically.
>
> Public domain, no telemetry. Repo: https://github.com/JesusGarcia9009/lethe-engineering
> PyPI: https://pypi.org/project/lethe-llm-context/
>
> Happy to answer questions about the design (Curator/Compactor/Archivist) or the honest
> limits (MCP can't rewrite the host's context — it offers explicit offload/recall tools).
