from __future__ import annotations

from math import ceil
from typing import Callable

from lethe.core.block import Block, Message
from lethe.adapters.base import Response


class FakeTokenCounter:
    """Deterministic: ~1 token per 4 characters of content."""

    def count(self, blocks: list[Block]) -> int:
        return sum(max(1, ceil(len(b.content) / 4)) for b in blocks)


class FakeAdapter:
    name = "fake"

    def __init__(
        self,
        scripted: list[str] | None = None,
        handler: Callable[[list[Message]], str] | None = None,
        context_window: int = 1000,
    ):
        self.context_window = context_window
        self.token_counter = FakeTokenCounter()
        self._scripted = list(scripted or [])
        self._handler = handler
        self._i = 0

    def complete(self, messages: list[Message], **kw) -> Response:
        if self._handler is not None:
            return Response(text=self._handler(messages))
        if self._i < len(self._scripted):
            text = self._scripted[self._i]
            self._i += 1
            return Response(text=text)
        return Response(text="")
