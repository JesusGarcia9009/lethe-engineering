from __future__ import annotations

from lethe.core.block import Block, Message

KIND_WEIGHT = {
    "note": 1.0,
    "text": 0.7,
    "file": 0.6,
    "tool_call": 0.6,
    "tool_result": 0.5,
    "image": 0.4,
}


def _parse_score(text: str, default: float = 0.5) -> float:
    try:
        v = float(text.strip().split()[0])
    except (ValueError, IndexError):
        return default
    return max(0.0, min(1.0, v))


class Curator:
    """Relevance scoring: heuristics blended with optional cheap model judgment."""

    def __init__(self, adapter=None, w_recency: float = 0.5, w_refs: float = 0.25,
                 w_kind: float = 0.1, w_model: float = 0.15):
        self.adapter = adapter
        self.w_recency = w_recency
        self.w_refs = w_refs
        self.w_kind = w_kind
        self.w_model = w_model if adapter is not None else 0.0

    def score(self, blocks: list[Block], now_step: int, goal: str) -> dict[str, float]:
        ref_counts: dict[str, int] = {}
        for b in blocks:
            for r in b.refs:
                ref_counts[r] = ref_counts.get(r, 0) + 1
        span = max(now_step, 1)
        out: dict[str, float] = {}
        for b in blocks:
            if b.pinned:
                out[b.id] = 1.0
                continue
            recency = max(0.0, 1.0 - (now_step - b.created_step) / span)
            refs = min(1.0, ref_counts.get(b.id, 0) / 2.0)
            kind = KIND_WEIGHT.get(b.kind, 0.5)
            model = self._model_score(b, goal) if self.w_model else 0.0
            out[b.id] = round(
                self.w_recency * recency
                + self.w_refs * refs
                + self.w_kind * kind
                + self.w_model * model,
                4,
            )
        return out

    def _model_score(self, block: Block, goal: str) -> float:
        prompt = (
            f"Goal: {goal}\nBlock:\n{block.content}\n"
            f"Rate 0.0-1.0 how relevant this block is to the goal. "
            f"Reply with only the number."
        )
        resp = self.adapter.complete([
            Message(role="user", blocks=[
                Block(id="q", role="user", kind="text", content=prompt, created_step=0)
            ])
        ])
        return _parse_score(resp.text)
