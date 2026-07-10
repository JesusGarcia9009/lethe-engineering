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


def test_cold_run_selects_leading_cold_contiguous_blocks():
    # now_step=7, span=7: score(step i) = 0.5*(i/7) + 0.1*0.5 (tool_result kind).
    # cold<0.25 holds for i in {0,1,2}; step3+ warmer; steps 6,7 protected.
    blocks = [_b(str(i), i, "x" * 40) for i in range(8)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=2))
    run = sched.cold_run(blocks, now_step=7, goal="g")
    assert [b.id for b in run] == ["0", "1", "2"]


def test_cold_run_excludes_pinned():
    blocks = [_b(str(i), i, "x" * 40) for i in range(6)]
    blocks[1].pinned = True
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=1))
    run = sched.cold_run(blocks, now_step=5, goal="g")
    assert "1" not in {b.id for b in run}


def test_cold_run_empty_when_all_recent_or_protected():
    blocks = [_b(str(i), i, "x" * 40) for i in range(3)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.25, keep_last_n_steps=3))
    run = sched.cold_run(blocks, now_step=2, goal="g")
    assert run == []


def test_plan_accepts_precomputed_scores():
    blocks = [_b(str(i), i, "x" * 40) for i in range(10)]
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(keep_last_n_steps=2))
    scores = sched.score(blocks, now_step=9, goal="g")
    kept, evicted = sched.plan(blocks, now_step=9, goal="g", scores=scores)
    assert sum(FakeTokenCounter().count([b]) for b in kept) <= 50


def test_cold_run_does_not_span_subgoal_boundary():
    # cold=0.95 makes steps 0-3 all cold; keep_last_n=1 protects step 4.
    blocks = [_b(str(i), i, "x" * 40) for i in range(5)]
    for b in blocks[:2]:
        b.meta["subgoal"] = "A"
    for b in blocks[2:4]:
        b.meta["subgoal"] = "B"
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.95, keep_last_n_steps=1))
    run = sched.cold_run(blocks, now_step=4, goal="g")
    sgs = {b.meta.get("subgoal") for b in run}
    assert run and len(sgs) == 1   # a run never mixes two subgoals


def test_cold_run_excludes_open_subgoal():
    blocks = [_b(str(i), i, "x" * 40) for i in range(4)]
    for b in blocks:
        b.meta["subgoal"] = "A"
    sched = Scheduler(Curator(), FakeTokenCounter(), budget=0.5, context_window=100,
                      thresholds=Thresholds(cold=0.95, keep_last_n_steps=1))
    run = sched.cold_run(blocks, now_step=3, goal="g", open_subgoal="A")
    assert run == []   # the open subgoal is never compacted
