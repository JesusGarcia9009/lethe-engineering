from lethe.core.block import Block, Message
from lethe.adapters.fake import FakeAdapter
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager


def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)


def make_cm():
    agent = FakeAdapter(context_window=100)
    return ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                          budget=0.5, triggers={"every_steps": 1, "on_budget": True})


def test_render_keeps_working_set_under_budget():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 40))   # 10 tok each -> 100 tok total
    msgs = ctx.render()
    used = ctx.stats()["tokens_with_lethe"]
    assert used <= 50
    assert all(isinstance(m, Message) for m in msgs)


def test_stats_reports_savings():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 40))
    ctx.render()
    s = ctx.stats()
    assert s["tokens_without_lethe"] == 100
    assert s["tokens_with_lethe"] <= 50
    assert s["evicted"] >= 1
