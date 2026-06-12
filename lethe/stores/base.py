from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from lethe.core.block import Block


@dataclass
class Note:
    id: str
    session: str
    summary: str
    covers: list[str] = field(default_factory=list)   # block ids it replaces
    tokens: int | None = None


class Store(Protocol):
    def put(self, block: Block) -> None: ...
    def get(self, handle: str) -> Block | None: ...
    def search(self, query: str, limit: int) -> list[Block]: ...
    def put_note(self, note: Note) -> None: ...
    def events(self, kind: str, payload: dict) -> None: ...
