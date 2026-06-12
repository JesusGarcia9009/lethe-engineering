from __future__ import annotations

import re
import uuid
from math import ceil

from lethe.core.block import Block
from lethe.agents.archivist import Archivist

_HEX4 = re.compile(r"^[0-9a-f]{4}$")


def simple_tokens(text: str) -> int:
    """Provider-agnostic token estimate (~1 token per 4 chars)."""
    return max(1, ceil(len(text) / 4))


class LetheMemory:
    """Provider-agnostic offload memory: archive big content, recall on demand.

    This is the pure logic behind the MCP tools — no MCP dependency, fully testable.
    """

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
