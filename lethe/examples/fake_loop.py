"""Watch LETHE work — no API key needed (uses the deterministic FakeAdapter).

    python -m lethe.examples.fake_loop

Plants a 'needle' fact, floods the context with noise, and prints the live
view each step so you can SEE blocks get paged out and the budget bar hold.
"""
from __future__ import annotations

from lethe.core.block import Block
from lethe.adapters.fake import FakeAdapter
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager
from lethe.viz.console import render_frame


def main() -> None:
    agent = FakeAdapter(context_window=400)
    cm = ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="Recordar el codigo de lanzamiento")
    ctx.add(Block(id="needle", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))
    ctx.pin("needle") if False else None  # try uncommenting pin to see it never evict

    budget_tokens = cm.scheduler.target_tokens()
    for i in range(1, 16):
        ctx.add(Block(id=f"s{i}", role="tool", kind="tool_result",
                      content=f"resultado verboso del paso {i} " * 6, created_step=i))
        ctx.render()
        s = ctx.stats()
        print("\n" + render_frame(ctx.blocks, goal=ctx.goal, step=i,
                                  used_tokens=s["tokens_with_lethe"],
                                  budget_tokens=budget_tokens, stats=s))

    print("\n>>> Recall 'launch code':", ctx.recall("launch code"))
    s = ctx.stats()
    print(f">>> sin LETHE {s['tokens_without_lethe']} tok  ->  "
          f"con LETHE {s['tokens_with_lethe']} tok  ({s['evicted']} bloques paginados)")


if __name__ == "__main__":
    main()
