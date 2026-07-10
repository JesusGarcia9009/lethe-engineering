# Announcement drafts / Borradores de anuncio

Copy-paste drafts for sharing LETHE. **You** post these — pick the platforms that fit.
Keep it honest: LETHE doesn't magically shrink a host's context; it gives the agent explicit
`archive` / `recall` tools (+ a guiding skill) so it offloads big outputs on its own.

Links to fill in:
- PyPI: https://pypi.org/project/lethe-llm-context/
- MCP Registry: https://registry.modelcontextprotocol.io  (server `io.github.JesusGarcia9009/lethe`)
- Repo: https://github.com/JesusGarcia9009/lethe-engineering

---

## 1. Reddit — r/ClaudeAI / r/mcp

**Title:** LETHE — an MCP server that lets Claude Code offload big tool outputs and recall them on demand (save tokens on long tasks)

**Body:**
> I kept hitting the same wall on long agent runs: the context fills with stale tool outputs —
> build logs, test dumps, files read 30 steps ago — and every turn re-sends that bloat.
>
> LETHE is a small MCP server that exposes three tools — `lethe_archive`, `lethe_recall`,
> `lethe_status`. The agent archives a huge output to a short handle (a tiny stub stays in
> context) and recalls it losslessly only when it actually needs it. There's a guiding skill so
> it happens near-automatically.
>
> Honest about the mechanism: an MCP server can't rewrite the host's context for you — it gives
> the model explicit offload/recall tools and a skill that tells it when to use them. In a local
> needle-in-haystack test that pattern cut resident tokens by ~88%.
>
> Install:
> ```
> pip install "lethe-llm-context[mcp]"
> claude mcp add lethe -- lethe-mcp
> ```
> Listed on the official MCP registry and PyPI. Repo + demo: <repo link>. Feedback welcome —
> especially on the recall heuristics.

---

## 2. Hacker News — Show HN

**Title:** Show HN: LETHE – context garbage collector for LLM agents (MCP server)

**Body:**
> LETHE manages an agent's live context like an OS manages virtual memory: it pages cold tool
> outputs to a SQLite store and leaves a stub/handle behind, so anything can be recalled on
> demand instead of bloating every turn.
>
> It ships as an MCP server (`lethe_archive` / `lethe_recall` / `lethe_status`) for Claude Code
> and Codex, plus a skill so the agent offloads on its own. Model-agnostic, stdlib-only core,
> Unlicense.
>
> I'm being upfront that MCP can't silently rewrite the host context — the win comes from giving
> the model explicit tools + guidance. A local needle test showed ~89% token reduction while
> still recovering the planted fact.
>
> Install: pip install "lethe-llm-context[mcp]" && claude mcp add lethe -- lethe-mcp
> Repo: <repo link>  ·  Would love critique on the eviction/recall scoring.

---

## 3. X / Twitter (thread)

1/ Long LLM agent runs die the same way: the context window fills with stale tool outputs and
every turn re-sends the bloat. Quality drops, cost climbs, then you hit the ceiling. 🧵

2/ LETHE is an MCP server that fixes the data, not the prompt. The agent archives a huge output
to a short handle — a tiny stub stays in context — and recalls it losslessly only when needed.

3/ Three tools: `lethe_archive` · `lethe_recall` · `lethe_status`, plus a skill so it happens
near-automatically in Claude Code / Codex.

4/ Honest mechanism: MCP can't rewrite a host's context for you. LETHE gives the model explicit
offload/recall tools + guidance. Local needle test: ~89% fewer resident tokens, fact still
recovered.

5/ Install:
pip install "lethe-llm-context[mcp]"
claude mcp add lethe -- lethe-mcp

On PyPI + the official MCP registry. Repo: <repo link> ⭐ if useful.

---

## 4. MCP Discord / community channels

> Sharing a small MCP server I built: **LETHE** — a context "garbage collector" for long agent
> runs. Tools: `lethe_archive` / `lethe_recall` / `lethe_status` + a guiding skill so the agent
> offloads big tool outputs and recalls them on demand. On PyPI and the official registry
> (`io.github.JesusGarcia9009/lethe`). `pip install "lethe-llm-context[mcp]"`. Repo: <repo link>.
> Feedback on the recall heuristics very welcome 🙏

---

## 5. LinkedIn (profesional, ES)

> Publiqué **LETHE**, un servidor MCP de código abierto para agentes LLM de larga duración.
>
> El problema: en tareas largas, la ventana de contexto se llena de outputs que ya no sirven
> (logs, dumps de tests, archivos leídos hace 30 pasos). Eso degrada la calidad, sube el costo y
> termina chocando con el límite del modelo.
>
> LETHE gestiona el contexto como un sistema operativo gestiona la memoria virtual: descarga los
> bloques fríos a un store externo y deja un "stub" con un handle, para recuperarlos bajo demanda
> sin perder nada. Expone tres herramientas (`lethe_archive`, `lethe_recall`, `lethe_status`) y
> una skill para que el agente lo haga casi solo.
>
> Ya está en PyPI y en el registro oficial de MCP. Instalación en dos líneas. Repo y demo:
> <repo link>. Toda crítica técnica es bienvenida.

---

### Tips
- Post when your audience is active; reply to every comment in the first hour.
- Lead with the problem, not the project. The token-savings number is the hook.
- Never overstate: say "the agent offloads", not "LETHE shrinks your context automatically".
- Pin the demo (GIF or the `mcp_demo` output) — visible proof converts.
