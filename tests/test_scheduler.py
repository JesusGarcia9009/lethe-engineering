from lethe.core.block import Block
from lethe.adapters.fake import FakeTokenCounter
from lethe.agents.curator import Curator
from lethe.core.scheduler import Scheduler, Thresholds


def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)


def test_evicts_lowest_scored_until_under_budget():
    # window 100 tokens, budget 0.5 -> target 50. Each block 40 chars = 10 tokens.
    blocks = [_b(str(i), i, "x" * 40) for i in range(10)]   # 10 blocks * 10 tok = 100 tok
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=2))
    kept, evicted = sched.plan(blocks, now_step=9, goal="g")
    assert sum(FakeTokenCounter().count([b]) for b in kept) <= 50
    # the two most-recent steps are protected
    assert {"8", "9"}.issubset({b.id for b in kept})


def test_pinned_never_evicted():
    pinned = _b("keep", 0, "y" * 200)
    pinned.pinned = True
    filler = [_b(str(i), i, "x" * 40) for i in range(1, 6)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.3, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=1))
    kept, evicted = sched.plan([pinned, *filler], now_step=5, goal="g")
    assert "keep" in {b.id for b in kept}
