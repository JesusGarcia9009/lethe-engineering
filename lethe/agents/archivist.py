from __future__ import annotations

import uuid

from lethe.core.block import Block, BlockState


def make_handle() -> str:
    return uuid.uuid4().hex[:4]


class Archivist:
    """Owns paging against the store: page-out, page-fault, lexical recall."""

    def __init__(self, store):
        self.store = store

    def page_out(self, block: Block) -> Block:
        if block.handle is None:
            block.handle = make_handle()
        block.state = BlockState.PAGED
        self.store.put(block)
        self.store.events("page_out", {"id": block.id, "handle": block.handle})
        label = block.meta.get("label", f"{block.kind} @step{block.created_step}")
        return Block(id=f"stub-{block.id}", role=block.role, kind="text",
                     content=f"[paged: {label} · handle={block.handle}]",
                     created_step=block.created_step,
                     handle=block.handle, meta={"stub_for": block.id})

    def page_fault(self, handle: str) -> Block | None:
        block = self.store.get(handle)
        if block is None:
            return None
        block.state = BlockState.REHYDRATED
        self.store.events("page_fault", {"handle": handle})
        return block

    def recall(self, query: str, limit: int = 5) -> list[Block]:
        return self.store.search(query, limit=limit)
