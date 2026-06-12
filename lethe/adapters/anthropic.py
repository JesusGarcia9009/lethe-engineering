from __future__ import annotations

from functools import lru_cache
from math import ceil

from lethe.core.block import Block, Message
from lethe.adapters.base import Response


class _AnthropicTokenCounter:
    def __init__(self, client, model: str):
        self.client = client
        self.model = model

    @lru_cache(maxsize=4096)
    def _count_text(self, text: str) -> int:
        try:
            r = self.client.messages.count_tokens(
                model=self.model,
                messages=[{"role": "user", "content": text or " "}])
            return r.input_tokens
        except Exception:
            return max(1, ceil(len(text) / 4))   # offline fallback

    def count(self, blocks: list[Block]) -> int:
        return sum(self._count_text(b.content) for b in blocks)


class AnthropicAdapter:
    name = "claude"

    def __init__(self, model: str = "claude-haiku-4-5", context_window: int = 200_000,
                 api_key: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.context_window = context_window
        self.token_counter = _AnthropicTokenCounter(self.client, model)

    def _to_native(self, messages: list[Message]) -> list[dict]:
        out = []
        for m in messages:
            text = "\n".join(b.content for b in m.blocks)
            role = "assistant" if m.role == "assistant" else "user"
            out.append({"role": role, "content": text})
        return out

    def complete(self, messages: list[Message], max_tokens: int = 1024, **kw) -> Response:
        r = self.client.messages.create(
            model=self.model, max_tokens=max_tokens,
            messages=self._to_native(messages))
        text = "".join(p.text for p in r.content if getattr(p, "type", "") == "text")
        return Response(text=text, raw=r)
