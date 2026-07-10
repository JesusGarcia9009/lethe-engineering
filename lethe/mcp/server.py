from __future__ import annotations

import os

from mcp.server.fastmcp import FastMCP

from lethe.stores.sqlite import SqliteStore
from lethe.mcp.service import LetheMemory

mcp = FastMCP("lethe")
_mem = LetheMemory(SqliteStore(os.environ.get("LETHE_DB", "./lethe.db")))


@mcp.tool()
def lethe_archive(content: str, label: str = "") -> dict:
    """Store a large output out of context; returns a short handle to recall it later.

    Use this for verbose tool results, file dumps, logs, or big API responses you will not
    need in full right away. Keep only the returned handle in your context.
    """
    return _mem.archive(content, label=label or None)


@mcp.tool()
def lethe_recall(query_or_handle: str) -> str:
    """Recall archived content by its short handle or by keyword search."""
    return _mem.recall(query_or_handle) or "[lethe: nothing found]"


@mcp.tool()
def lethe_status() -> dict:
    """Report how much has been archived and how many tokens were offloaded."""
    return _mem.status()


def main() -> None:
    """Console entry point: `lethe-mcp` (registered in pyproject.toml)."""
    mcp.run()


if __name__ == "__main__":
    main()
