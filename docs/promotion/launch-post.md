# Launch blog post (dev.to / Medium / personal blog)

> The SEO centerpiece. Its job is to **rank for the query a developer actually types** —
> "how to reduce token usage in Claude Code on long tasks", "save context window tokens",
> "MCP server to offload large tool outputs". The title IS the SEO. Post it on dev.to (canonical),
> then cross-post to Medium/Hashnode with a canonical link back. Cross-link from the Reddit/HN
> drafts in `../announcements.md`.
>
> Keep it honest — the same mechanism note the README uses. Update the token numbers if the
> needle eval changes.

---

**Title:** How I cut token usage on long Claude Code / Codex tasks by ~88% (an MCP context garbage collector)

**Tags:** llm, claudecode, mcp, ai

**Canonical:** your blog URL

---

If you run long agent tasks in Claude Code or Codex — multi-file refactors, research loops,
anything that takes dozens of tool calls — you've paid the tax: the context window fills up with
**stale tool outputs**. Build logs you read once. A 900-line JSON dump you needed for one step. A
file you opened 30 steps ago. All of it rides along in every single turn.

That costs you three ways:

1. **Money.** Every turn re-sends the whole bloated history. Cost grows super-linearly with task
   length.
2. **Quality.** The "lost in the middle" effect — the relevant tokens get buried under noise and
   the model's attention degrades.
3. **A hard wall.** Long enough tasks hit the context ceiling and the agent breaks.

I got tired of this, so I built **LETHE** — a context garbage collector for LLM agents. This post
is how it works, how to try it in two lines, and — importantly — an honest account of what it
does and doesn't do.

## The idea: treat the context window like RAM

An operating system doesn't keep everything in physical RAM. It keeps the *working set* resident
and pages cold stuff out to disk, bringing it back on demand when you touch it. LETHE does the
same thing to your agent's context:

| Operating system | LETHE |
|---|---|
| Physical RAM | The context window |
| Disk | An external SQLite store |
| Page-table entry | A tiny stub/handle left in context |
| Page-in on fault | Recalling an archived block |
| Cold-page compression | Summarizing a run of finished steps into one dense note |

Concretely: when a tool output is big and you won't need all of it next step, LETHE moves it out
of the context window and leaves a short handle behind. When you *do* need it again, you recall it
by handle or by keyword — **losslessly**. Nothing is ever deleted.

## Try it in two lines (no API key for the demo)

LETHE ships as an **MCP server**, so it plugs straight into Claude Code:

```bash
pip install "lethe-llm-context[mcp]"
claude mcp add lethe -- lethe-mcp
```

(For Codex, add an MCP block to `~/.codex/config.toml` — the repo has the snippet.)

It exposes three tools — `lethe_archive`, `lethe_recall`, `lethe_status` — and ships a small
guiding **skill** that tells the agent *when* to offload, so it happens near-automatically instead
of you babysitting it.

Want to see the mechanism before installing anything? There's a no-API-key demo:

```bash
python -m lethe.examples.mcp_demo
```

```text
The agent runs 4 commands. Each returns a wall of text:

  → build.log     857 tok in context  —archive→  stub '[paged: build.log | handle=2f258c57]'
  → pytest.txt    479 tok in context  —archive→  stub '[paged: pytest.txt | handle=145256e9]'
  → db_dump.json  829 tok in context  —archive→  stub '[paged: db_dump.json | handle=12dfba94]'
  → trace.txt     414 tok in context  —archive→  stub '[paged: trace.txt | handle=d86e8b4e]'

30 steps later the agent needs a buried fact. It recalls by keyword:
  lethe_recall("launch_code")  →  found launch_code = 4242 (rehydrated losslessly)

  without LETHE :  2579 tok    with LETHE : 38 tok    saved: 2541 tok (-99%)
```

## Does it actually work? The needle test

Marketing numbers are cheap, so LETHE ships the proof as a test you can run yourself
(`python -m lethe.evals.needle`). It plants a fact at step 0, buries it under 50 noisy steps that
force compaction and paging, then queries it at the end:

- Working set held **under budget the entire run**.
- Resident tokens: **1721 → 199 (~88% reduction)**.
- The planted fact was **recovered losslessly** after being evicted and compacted.

Under the hood a **Curator** scores each block's relevance (recency, whether later steps cited it,
block kind), a **Compactor** folds cold finished runs into dense notes, and an **Archivist** pages
the rest to SQLite — orchestrated to keep the working set under a token budget.

## The honest part (please read this)

I want to be straight about the mechanism, because there's a lot of hand-wavy "AI memory"
marketing out there:

**An MCP server cannot silently rewrite your host's context window.** It exposes tools the model
chooses to call; results flow back into context. LETHE works by giving the agent explicit
`archive` / `recall` tools plus a skill that makes using them near-automatic — **not** by magic
interception.

And about scope: today LETHE ships two things that genuinely work — the MCP offload/recall server,
and a Python library that runs the in-loop Curator + Compactor + lossless paging. The bigger
vision in the design doc (multi-provider ensembles, embedding-based semantic recall, a one-line
`wrap()`) is **roadmap, not current state** — and the README says so with an explicit status
table. If you install it expecting the moon, I'd rather you know now.

## How it compares

Agent-memory libraries (Mem0, Zep, Letta) persist facts *across sessions*. LETHE targets the
opposite problem: managing the **live, in-session working context** of a running loop — what to
keep in the window *right now*. It's complementary to a long-term memory product, not a competitor.

## Try it / tear it apart

It's public domain (Unlicense), stdlib-only core, no telemetry.

- Repo + demo: https://github.com/JesusGarcia9009/lethe-engineering
- PyPI: https://pypi.org/project/lethe-llm-context/
- Listed on the official MCP registry as `io.github.JesusGarcia9009/lethe`

I'd genuinely love critique on the eviction/recall heuristics — that's the part with the most room
to be smarter. If it saves you tokens, a ⭐ helps others find it.
