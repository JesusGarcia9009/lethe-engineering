# LETHE MCP Server (v0.6.0) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or executing-plans.

**Goal:** Expose LETHE as an MCP server (`lethe_archive`/`lethe_recall`/`lethe_status`) for Claude Code and Codex, plus a guiding skill, so agents offload large outputs and save tokens.

**Architecture:** All logic in a pure `LetheMemory` service (reuses SqliteStore + Archivist), unit-tested without the MCP SDK; a thin FastMCP `server.py` wires tools to it; integration docs make install two lines.

**Tech Stack:** Python 3.14, stdlib, optional `mcp` SDK (extra `[mcp]`), pytest.

---

## Task 1: `LetheMemory` service

**Files:** Create `lethe/mcp/__init__.py`, `lethe/mcp/service.py`; Test `tests/test_mcp_service.py`

- [ ] **Step 1: failing test**

```python
# tests/test_mcp_service.py
from lethe.stores.memory import MemoryStore
from lethe.mcp.service import LetheMemory, simple_tokens


def mem():
    return LetheMemory(MemoryStore())


def test_archive_returns_handle_and_saving():
    m = mem()
    r = m.archive("x" * 4000, label="big.log")
    assert len(r["handle"]) == 4
    assert r["tokens_saved"] > 0
    assert m.recall(r["handle"]) == "x" * 4000


def test_recall_by_keyword():
    m = mem()
    m.archive("the launch code is 4242")
    assert "4242" in m.recall("launch code")


def test_recall_unknown_returns_none():
    assert mem().recall("zzzz") is None


def test_status_counts_and_accumulates():
    m = mem()
    m.archive("a" * 400)
    m.archive("b" * 800)
    s = m.status()
    assert s["archived"] == 2
    assert s["tokens_offloaded"] == simple_tokens("a" * 400) + simple_tokens("b" * 800)


def test_simple_tokens_deterministic():
    assert simple_tokens("abcd") == 1 and simple_tokens("abcdefgh") == 2
```

- [ ] **Step 2: run, expect fail** — `python -m pytest tests/test_mcp_service.py -q` → ModuleNotFound.

- [ ] **Step 3: implement**

```python
# lethe/mcp/service.py
from __future__ import annotations
import re, uuid
from math import ceil
from lethe.core.block import Block
from lethe.agents.archivist import Archivist

_HEX4 = re.compile(r"^[0-9a-f]{4}$")


def simple_tokens(text: str) -> int:
    return max(1, ceil(len(text) / 4))


class LetheMemory:
    """Provider-agnostic offload memory: archive big content, recall on demand."""

    def __init__(self, store, session: str = "default"):
        self.archivist = Archivist(store)
        self.session = session
        self._archived = 0
        self._tokens_offloaded = 0

    def archive(self, content: str, label: str | None = None) -> dict:
        tokens = simple_tokens(content)
        block = Block(id=uuid.uuid4().hex, role="tool", kind="tool_result",
                      content=content, created_step=self._archived,
                      tokens=tokens, meta={"label": label or "", "session": self.session})
        stub = self.archivist.page_out(block)
        self._archived += 1
        self._tokens_offloaded += tokens
        return {"handle": block.handle, "tokens_saved": tokens,
                "label": label or "", "stub": stub.content}

    def recall(self, query_or_handle: str) -> str | None:
        if _HEX4.match(query_or_handle):
            block = self.archivist.page_fault(query_or_handle)
            return block.content if block else None
        hits = self.archivist.recall(query_or_handle)
        return hits[0].content if hits else None

    def status(self) -> dict:
        return {"archived": self._archived,
                "tokens_offloaded": self._tokens_offloaded,
                "session": self.session}
```

- [ ] **Step 4: run, expect pass.** **Step 5: commit** `feat: LetheMemory offload service for MCP`.

---

## Task 2: FastMCP server

**Files:** Create `lethe/mcp/server.py`; Test `tests/test_mcp_server_smoke.py`

- [ ] **Step 1: smoke test (skips without SDK)**

```python
# tests/test_mcp_server_smoke.py
import importlib.util, pytest

def test_server_imports_if_sdk_present():
    if importlib.util.find_spec("mcp") is None:
        pytest.skip("mcp SDK not installed")
    import lethe.mcp.server as s
    assert s.mcp is not None
```

- [ ] **Step 2: implement**

```python
# lethe/mcp/server.py
from __future__ import annotations
import os
from mcp.server.fastmcp import FastMCP
from lethe.stores.sqlite import SqliteStore
from lethe.mcp.service import LetheMemory

mcp = FastMCP("lethe")
_mem = LetheMemory(SqliteStore(os.environ.get("LETHE_DB", "./lethe.db")))


@mcp.tool()
def lethe_archive(content: str, label: str = "") -> dict:
    """Store a large output out of context; returns a short handle to recall it later."""
    return _mem.archive(content, label=label or None)


@mcp.tool()
def lethe_recall(query_or_handle: str) -> str:
    """Recall archived content by its 4-char handle or by keyword search."""
    return _mem.recall(query_or_handle) or "[lethe: nothing found]"


@mcp.tool()
def lethe_status() -> dict:
    """Report how much has been archived and how many tokens were offloaded."""
    return _mem.status()


if __name__ == "__main__":
    mcp.run()
```

- [ ] **Step 3: run smoke test** (skips if no SDK). **Step 4: commit** `feat: FastMCP stdio server exposing lethe tools`.

---

## Task 3: Guiding skill + install snippets

**Files:** Create `integrations/claude-code/SKILL.md`, `integrations/claude-code/mcp-config.md`, `integrations/codex/mcp-config.md`

- [ ] **Step 1: write SKILL.md** (offload instruction, ~1500 token threshold — full text in spec §7).
- [ ] **Step 2: write the two mcp-config.md** snippets (spec §8).
- [ ] **Step 3: commit** `docs: guiding skill and MCP install snippets for Claude Code and Codex`.

---

## Task 4: Packaging + README + release v0.6.0

**Files:** Modify `pyproject.toml` (add `[mcp]` extra), `README.md`, `CHANGELOG.md`

- [ ] **Step 1:** add `mcp = ["mcp>=1.2"]` to optional-dependencies.
- [ ] **Step 2:** README — "Use it in Claude Code / Codex" section with the two-line install.
- [ ] **Step 3:** CHANGELOG — move `[Unreleased]` → `[0.6.0]`; bump version to 0.6.0.
- [ ] **Step 4:** run full suite; **Step 5:** commit, tag `v0.6.0`, push.

---

## Self-review
- Spec coverage: service (T1), server (T2), skill+snippets (T3), packaging/release (T4) — all spec sections mapped.
- Type consistency: `LetheMemory.archive/recall/status`, `simple_tokens`, tool names `lethe_archive/lethe_recall/lethe_status` identical across tasks.
