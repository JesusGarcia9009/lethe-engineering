from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from lethe.core.block import Block, Message


@runtime_checkable
class TokenCounter(Protocol):
    def count(self, blocks: list[Block]) -> int: ...


@dataclass
class Response:
    text: str
    raw: Any = None


@runtime_checkable
class ProviderAdapter(Protocol):
    name: str
    context_window: int
    token_counter: TokenCounter

    def complete(self, messages: list[Message], **kw: Any) -> Response: ...
