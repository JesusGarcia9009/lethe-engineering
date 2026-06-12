from __future__ import annotations

from lethe.core.block import Block
from lethe.stores.base import Note


class MemoryStore:
    def __init__(self):
        self._by_handle: dict[str, Block] = {}
        self._by_id: dict[str, Block] = {}
        self.notes: dict[str, Note] = {}
        self.event_log: list[dict] = []

    def put(self, block: Block) -> None:
        self._by_id[block.id] = block
        if block.handle:
            self._by_handle[block.handle] = block

    def get(self, handle: str) -> Block | None:
        return self._by_handle.get(handle)

    def search(self, query: str, limit: int) -> list[Block]:
        q = query.lower()
        hits = [b for b in self._by_id.values() if q in b.content.lower()]
        hits.sort(key=lambda b: b.created_step)
        return hits[:limit]

    def put_note(self, note: Note) -> None:
        self.notes[note.id] = note

    def events(self, kind: str, payload: dict) -> None:
        self.event_log.append({"kind": kind, "payload": payload})
