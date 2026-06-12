from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal


class BlockState(Enum):
    ACTIVE = "active"
    WARM = "warm"
    COMPACTED = "compacted"
    PAGED = "paged"
    REHYDRATED = "rehydrated"


Role = Literal["system", "user", "assistant", "tool", "reasoning"]
Kind = Literal["text", "tool_call", "tool_result", "file", "image", "note"]


@dataclass
class Block:
    id: str
    role: Role
    kind: Kind
    content: str
    created_step: int
    pinned: bool = False
    state: BlockState = BlockState.ACTIVE
    tokens: int | None = None
    handle: str | None = None
    refs: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)


@dataclass
class Message:
    role: str
    blocks: list[Block] = field(default_factory=list)
