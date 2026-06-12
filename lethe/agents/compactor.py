from __future__ import annotations

import uuid

from lethe.core.block import Block, Message
from lethe.stores.base import Note


class Compactor:
    """Replaces a contiguous run of completed cold blocks with one dense note."""

    def __init__(self, adapter):
        self.adapter = adapter

    def compact(self, run: list[Block], session: str) -> Note | None:
        if not run or any(b.pinned for b in run):
            return None
        joined = "\n---\n".join(b.content for b in run)
        prompt = (
            "Summarize these completed agent steps. Preserve decisions, results, "
            "and any open threads. Be dense.\n\n" + joined
        )
        summary = self.adapter.complete([
            Message(role="user", blocks=[
                Block(id="q", role="user", kind="text", content=prompt, created_step=0)
            ])
        ]).text
        orig_tokens = self.adapter.token_counter.count(run)
        note_block = Block(id="n", role="assistant", kind="note",
                           content=summary, created_step=run[-1].created_step)
        note_tokens = self.adapter.token_counter.count([note_block])
        if note_tokens >= orig_tokens:        # no negative-savings compaction
            return None
        return Note(id=str(uuid.uuid4())[:8], session=session,
                    summary=summary, covers=[b.id for b in run], tokens=note_tokens)
