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


def test_compaction_folds_cold_run_into_a_note_losslessly():
    # A summarizing curator so the consolidation note carries real text.
    agent = FakeAdapter(context_window=400, handler=lambda msgs: "SUMMARY of early steps")
    store = MemoryStore()
    cm = ContextManager(agent=agent, curator=agent, store=store,
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="find the code later")
    ctx.add(Block(id="needle", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))
    for i in range(1, 12):
        ctx.add(Block(id=f"n{i}", role="tool", kind="tool_result",
                      content="filler " * 20, created_step=i))
        ctx.render()

    s = ctx.stats()
    # at least one consolidation note was created, covering >= 2 blocks
    assert s["notes"] >= 1 and s["compacted"] >= 2
    # the note persisted with the real summary text
    saved_notes = list(store.notes.values())
    assert saved_notes and "SUMMARY" in saved_notes[0].summary
    # the buried fact is still recoverable losslessly
    got = ctx.recall("launch code")
    assert got is not None and "4242" in got.content
    # budget was respected
    assert s["tokens_with_lethe"] <= cm.scheduler.target_tokens()


def test_session_protects_open_subgoal_from_compaction():
    # Identical setup to test_compaction_folds... (which produces notes >= 1),
    # the ONLY difference being an open subgoal — so nothing may compact.
    agent = FakeAdapter(context_window=400, handler=lambda msgs: "SUMMARY of early steps")
    cm = ContextManager(agent=agent, curator=agent, store=MemoryStore(),
                        budget=0.5, triggers={"every_steps": 1, "on_budget": True})
    ctx = cm.session(goal="g", subgoal="A")
    ctx.add(Block(id="a0", role="user", kind="text",
                  content="the launch code is 4242", created_step=0))
    for i in range(1, 12):
        ctx.add(Block(id=f"a{i}", role="tool", kind="tool_result",
                      content="filler " * 20, created_step=i))
        ctx.render()
    # everything belongs to the still-open subgoal A -> no consolidation notes
    assert ctx.stats()["notes"] == 0
    # sanity: budget was still held (via paging, not compaction)
    assert ctx.stats()["tokens_with_lethe"] <= cm.scheduler.target_tokens()


def test_set_subgoal_changes_open_subgoal():
    cm = make_cm()
    ctx = cm.session(goal="g", subgoal="A")
    assert ctx.subgoal == "A"
    ctx.set_subgoal("B")
    assert ctx.subgoal == "B"
