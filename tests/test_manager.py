from lethe.core.block import Block, Message
from lethe.adapters.fake import FakeAdapter
from lethe.adapters.base import Response
from lethe.stores.memory import MemoryStore
from lethe.core.manager import ContextManager


def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)


def make_cm():
    # window 1000, budget 0.3 -> target 300 tokens.
    agent = FakeAdapter(context_window=1000)
    return ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                          budget=0.3, triggers={"every_steps": 1, "on_budget": True})


def test_render_keeps_working_set_under_budget():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 400))   # 100 tok each -> 1000 tok total
    msgs = ctx.render()
    used = ctx.stats()["tokens_with_lethe"]
    assert used <= 300                       # target = 0.3 * 1000
    assert all(isinstance(m, Message) for m in msgs)


def test_stats_reports_savings():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 400))
    ctx.render()
    s = ctx.stats()
    assert s["tokens_without_lethe"] == 1000        # every block counted once, full size
    assert s["tokens_with_lethe"] < s["tokens_without_lethe"]
    assert s["evicted"] >= 1


def test_observe_referenced_handle_pages_block_back_in():
    cm = make_cm()
    ctx = cm.session(goal="g")
    for i in range(10):
        ctx.add(_b(str(i), i, "x" * 400))
    ctx.render()
    paged_handles = list(cm.store._by_handle.keys())
    assert paged_handles
    h = paged_handles[0]
    ctx.observe(Response(text=f"I need handle={h} again"))
    assert any(b.handle == h and not b.meta.get("stub_for") for b in ctx.blocks)


def test_recall_query_returns_block():
    cm = make_cm()
    ctx = cm.session(goal="g")
    ctx.add(_b("needle", 0, "the needle is 4242"))
    for i in range(1, 12):
        ctx.add(_b(str(i), i, "x" * 400))
    ctx.render()
    got = ctx.recall("needle")
    assert got is not None and "4242" in got.content
