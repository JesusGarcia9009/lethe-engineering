# LETHE MCP Server — Design Spec (v0.6.0)

> Status: approved · Target builder: Claude Code · Date: 2026-06-12
> Parent: `2026-06-12-lethe-vertical-slice-design.md` · Builds on released v0.5.0
> North star: **adoption** — frictionless install so people actually save tokens
> (modeled on github.com/obra/superpowers).

---

## 1. Purpose

Expose LETHE as a **Model Context Protocol (MCP) server** so it plugs into both **Claude Code
and Codex** through a single piece. Paired with a guiding **skill**, it lets an agent offload
large tool outputs out of its context and recall them on demand — saving tokens in real,
long-running sessions.

## 2. Honest mechanism (what MCP can and cannot do)

An MCP server exposes **tools the model chooses to call**; tool results flow *into* context.
An MCP server **cannot** intercept or rewrite the host's context window. Therefore LETHE-via-MCP
uses an **explicit offload model**:

1. The agent gets a large tool output.
2. It calls `lethe_archive(content)` → LETHE stores it and returns a short **handle**
   (~10 tokens) instead of keeping the full payload.
3. Later it calls `lethe_recall(query_or_handle)` → LETHE returns the original content.

A **skill** instructs the agent to do this automatically for outputs above a threshold, so the
saving happens without per-turn user prompting — within what the host allows. No magic
interception; an honest, working token saver.

## 3. Scope

### In scope (v0.6.0)
- `lethe/mcp/service.py` — `LetheMemory`: pure, testable archive/recall/status logic.
- `lethe/mcp/server.py` — thin FastMCP (stdio) wrapper exposing the tools.
- Tools: `lethe_archive`, `lethe_recall`, `lethe_status`.
- `integrations/claude-code/SKILL.md` — the guiding skill (offload large outputs).
- `integrations/claude-code/mcp-config.md` and `integrations/codex/mcp-config.md` — copy-paste
  install snippets.
- Optional `[mcp]` dependency extra (official `mcp` SDK).
- README install section + CHANGELOG entry, released as **v0.6.0**.

### Out of scope (later)
- `lethe_pin` (no role in the offload model yet).
- Publishing to PyPI / MCP registry (its own follow-up release).
- Auto-installer script (deferred; manual snippet first).
- Provider-exact token counting in the server (uses an honest estimate).

## 4. Architecture

```
lethe/
  mcp/
    __init__.py
    service.py   # LetheMemory — reuses SqliteStore + Archivist; NO mcp dependency
    server.py    # FastMCP server (stdio); imports mcp SDK; thin
integrations/
  claude-code/ SKILL.md  mcp-config.md
  codex/       mcp-config.md
```

Boundary rule: **all logic lives in `service.py`** (no MCP import), so it is unit-tested
without the SDK. `server.py` only wires tools to service methods and runs the transport.

## 5. `LetheMemory` (service.py)

```python
class LetheMemory:
    def __init__(self, store, session: str = "default"): ...
    def archive(self, content: str, label: str | None = None) -> dict:
        # -> {"handle": "a3f9", "tokens_saved": 1820, "label": "..."}
    def recall(self, query_or_handle: str) -> str | None:
        # 4-hex handle -> exact page_fault; otherwise lexical search (first hit)
    def status(self) -> dict:
        # -> {"archived": 12, "tokens_offloaded": 21400, "session": "default"}
```

- Reuses `Archivist.page_out` / `page_fault` / `recall` and `SqliteStore`.
- `archive` builds a `Block` (kind chosen from `label`/default `tool_result`), pages it out,
  returns the handle and an **estimated** token saving.
- Token estimate: `simple_tokens(text) = max(1, ceil(len(text)/4))`, provider-agnostic and
  labeled as an estimate. Honest: the host's real count may differ.

## 6. `server.py` (FastMCP, stdio)

```python
from mcp.server.fastmcp import FastMCP
from lethe.stores.sqlite import SqliteStore
from lethe.mcp.service import LetheMemory

mcp = FastMCP("lethe")
mem = LetheMemory(SqliteStore(os.environ.get("LETHE_DB", "./lethe.db")))

@mcp.tool()
def lethe_archive(content: str, label: str = "") -> dict: ...
@mcp.tool()
def lethe_recall(query_or_handle: str) -> str: ...
@mcp.tool()
def lethe_status() -> dict: ...

if __name__ == "__main__":
    mcp.run()
```

`server.py` is not imported by tests (it needs the SDK). A smoke test asserts it imports only
when `mcp` is installed; otherwise skipped.

## 7. The guiding skill (`integrations/claude-code/SKILL.md`)

A short skill the user installs alongside the server. Core instruction:

> When a tool result exceeds ~1500 tokens and you will not need all of it immediately, call
> `lethe_archive` with that content and keep only the returned handle. Recall it with
> `lethe_recall(handle)` or `lethe_recall("<keywords>")` when you need it again. Prefer
> archiving verbose file dumps, logs, and large API responses.

Threshold (~1500 tokens) is stated in the skill and easy to edit.

## 8. Install snippets (distribution)

`integrations/claude-code/mcp-config.md`:

```bash
pip install "lethe[mcp]"
claude mcp add lethe -- python -m lethe.mcp.server
```

`integrations/codex/mcp-config.md`: the equivalent Codex `~/.codex/config.toml` MCP block
pointing at `python -m lethe.mcp.server`.

These make install a **two-line** operation — the adoption goal.

## 9. Testing (TDD)

`tests/test_mcp_service.py` (uses `MemoryStore` and a temp `SqliteStore`, no SDK):
- `archive` returns a 4-hex handle and a positive `tokens_saved`; content retrievable.
- `recall` by exact handle returns the original content.
- `recall` by keyword returns the matching content via lexical search.
- `recall` of an unknown handle/keyword returns `None`.
- `status` counts archived items and accumulates `tokens_offloaded`.
- token estimate is deterministic.

`tests/test_mcp_server_smoke.py`:
- if `mcp` importable, importing `lethe.mcp.server` succeeds and exposes the 3 tools;
  else `pytest.skip`.

## 10. Acceptance criteria

1. `service.py` tests pass with no MCP SDK installed.
2. Importing `lethe.mcp.service` works without the `mcp` package.
3. With `[mcp]` installed, `python -m lethe.mcp.server` starts a stdio MCP server exposing
   `lethe_archive`, `lethe_recall`, `lethe_status`.
4. README documents the two-line install for Claude Code and Codex; SKILL.md present.
5. Released as **v0.6.0** with CHANGELOG entry and git tag.

## 11. Risks

- **Agent doesn't call the tools** → no saving. Mitigation: the skill makes it default
  behavior; `lethe_status` lets users verify it's working.
- **Recall misses paraphrased queries** (lexical only). Mitigation: exact-handle recall is
  always reliable; embeddings come in a later phase.
- **MCP SDK API drift.** Mitigation: keep `server.py` thin; all logic in tested `service.py`.
