---
name: lethe-offload
description: Use throughout long sessions to keep the context window small — archive large tool outputs to LETHE and recall them on demand, saving tokens.
---

# LETHE Offload

You have a LETHE MCP memory available. Use it to keep your context window small during long
tasks, which saves tokens and preserves your attention for what matters.

## The rule

When a tool result, file read, log, or API response is **large (roughly > 1500 tokens)** and
you will **not need all of it in the next step or two**, archive it instead of keeping it:

1. Call `lethe_archive(content=<the big text>, label=<short name>)`.
2. Keep only the returned **handle** (e.g. `handle=a3f9`) in your reasoning. Drop the full text.
3. When you need it again, call `lethe_recall("a3f9")` (by handle) or
   `lethe_recall("<keywords>")` (by content) to get it back.

## When to archive

- ✅ Verbose file dumps you only needed to scan once.
- ✅ Long logs, stack traces, large JSON/API responses.
- ✅ Earlier step outputs that are "done" but might be referenced later.

## When NOT to archive

- ❌ The current task instructions or active goal.
- ❌ Small outputs (under ~1500 tokens) — archiving them saves nothing.
- ❌ Anything you are about to use in the very next step.

## Check your savings

Call `lethe_status()` to see how many items you have archived and how many tokens you have
offloaded so far. LETHE never deletes anything — archived content is always recoverable.
