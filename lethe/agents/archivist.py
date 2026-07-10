from __future__ import annotations

import uuid

from lethe.core.block import Block, BlockState


HANDLE_LEN = 8   # 32 bits: ~65k archives before a 50% birthday-collision chance


def make_handle(n: int = HANDLE_LEN) -> str:
    return uuid.uuid4().hex[:n]


class Archivist:
    """Owns paging against the store: page-out, page-fault, lexical recall."""

    def __init__(self, store):
        self.store = store

    def _fresh_handle(self) -> str:
        """A handle no block currently holds — guarantees recall never collides."""
        for _ in range(1000):
            h = make_handle()
            if self.store.get(h) is None:
                return h
        raise RuntimeError("could not allocate a unique handle")   # pragma: no cover

    def page_out(self, block: Block) -> Block:
        if block.handle is None:
            block.handle = self._fresh_handle()
        block.state = BlockState.PAGED
        self.store.put(block)
        self.store.events("page_out", {"id": block.id, "handle": block.handle})
        label = block.meta.get("label", f"{block.kind} @step{block.created_step}")
        return Block(id=f"stub-{block.id}", role=block.role, kind="text",
                     content=f"[paged: {label} | handle={block.handle}]",
                     created_step=block.created_step,
                     handle=block.handle, meta={"stub_for": block.id})

    def compact_out(self, block: Block) -> str:
        """Store a block that a consolidation note now represents. Lossless, no stub."""
        if block.handle is None:
            block.handle = self._fresh_handle()
        block.state = BlockState.COMPACTED
        self.store.put(block)
        self.store.events("compact_out", {"id": block.id, "handle": block.handle})
        return block.handle

    def page_fault(self, handle: str) -> Block | None:
        block = self.store.get(handle)
        if block is None:
            return None
        block.state = BlockState.REHYDRATED
        self.store.events("page_fault", {"handle": handle})
        return block

    def recall(self, query: str, limit: int = 5) -> list[Block]:
        return self.store.search(query, limit=limit)
