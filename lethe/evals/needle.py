"""Needle-in-a-haystack eval: the value proof.

Plant a fact at step 0, bury it under many noisy steps that force compaction
and paging, then prove the fact is still recoverable — under budget the whole time.
"""
from __future__ import annotations

from lethe.core.block import Block
from lethe.adapters.fake import FakeAdapter
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager

NEEDLE = "the launch code is 4242"


def run_needle(steps: int = 50) -> dict:
    agent = FakeAdapter(context_window=400)
    cm = ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="find the launch code later")
    ctx.add(Block(id="needle", role="user", kind="text", content=NEEDLE, created_step=0))
    max_used = 0
    for i in range(1, steps):
        ctx.add(Block(id=f"noise{i}", role="tool", kind="tool_result",
                      content="filler " * 20, created_step=i))
        ctx.render()
        max_used = max(max_used, ctx.stats()["tokens_with_lethe"])
    recalled = ctx.recall("launch code")
    s = ctx.stats()
    s["max_tokens_with_lethe"] = max_used
    s["target_tokens"] = cm.scheduler.target_tokens()
    s["needle_recovered"] = bool(recalled and "4242" in recalled.content)
    return s


if __name__ == "__main__":
    result = run_needle()
    print(result)
