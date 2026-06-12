"""Run a long synthetic loop against real Claude and watch LETHE manage context.

Usage:
    PowerShell:  $env:ANTHROPIC_API_KEY="sk-..."
    Bash:        export ANTHROPIC_API_KEY=sk-...
    python -m lethe.examples.claude_loop
"""
from __future__ import annotations

import os

from lethe.core.block import Block
from lethe.stores.sqlite import SqliteStore
from lethe.core.manager import ContextManager
from lethe.viz.console import render_frame


def main() -> None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Set ANTHROPIC_API_KEY to run the real loop.")
        return

    from lethe.adapters.anthropic import AnthropicAdapter

    agent = AnthropicAdapter(model="claude-opus-4-8")
    curator = AnthropicAdapter(model="claude-haiku-4-5")
    cm = ContextManager(agent=agent, curator=curator,
                        store=SqliteStore("./lethe.db"),
                        budget=0.5, triggers={"every_steps": 3, "on_budget": True})

    ctx = cm.session(goal="Track the launch code through a long task")
    ctx.add(Block(id="needle", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))

    budget_tokens = int(agent.context_window * 0.5)
    for i in range(1, 30):
        ctx.add(Block(id=f"s{i}", role="tool", kind="tool_result",
                      content=f"step {i} produced some verbose output " * 10,
                      created_step=i))
        ctx.render()
        s = ctx.stats()
        print("\n" + render_frame(ctx.blocks, goal=ctx.goal, step=i,
                                  used_tokens=s["tokens_with_lethe"],
                                  budget_tokens=budget_tokens, stats=s))

    print("\nRecall 'launch code':", ctx.recall("launch code"))


if __name__ == "__main__":
    main()
