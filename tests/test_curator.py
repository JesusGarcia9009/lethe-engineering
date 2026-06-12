from lethe.core.block import Block
from lethe.agents.curator import Curator
from lethe.adapters.fake import FakeAdapter


def _b(id, step, content="x", kind="tool_result", pinned=False, refs=None):
    return Block(id=id, role="tool", kind=kind, content=content,
                 created_step=step, pinned=pinned, refs=refs or [])


def test_pinned_block_scores_one():
    c = Curator()
    b = _b("p", 0, pinned=True)
    assert c.score([b], now_step=10, goal="anything")[b.id] == 1.0


def test_recent_block_scores_higher_than_old():
    c = Curator()
    old = _b("old", 0)
    new = _b("new", 9)
    s = c.score([old, new], now_step=10, goal="g")
    assert s["new"] > s["old"]


def test_referenced_block_gets_keep_boost():
    c = Curator()
    cited = _b("cited", 0)
    citer = _b("citer", 1, refs=["cited"])
    s = c.score([cited, citer], now_step=10, goal="g")
    baseline = c.score([_b("cited", 0)], now_step=10, goal="g")["cited"]
    assert s["cited"] > baseline


def test_model_blend_overrides_toward_model_score():
    adapter = FakeAdapter(handler=lambda msgs: "1.0")
    c = Curator(adapter=adapter, w_model=1.0, w_recency=0.0, w_refs=0.0, w_kind=0.0)
    old = _b("old", 0)
    s = c.score([old], now_step=100, goal="g")
    assert s["old"] == 1.0


def test_model_parse_clamps_bad_output():
    adapter = FakeAdapter(handler=lambda msgs: "not a number")
    c = Curator(adapter=adapter, w_model=1.0, w_recency=0.0, w_refs=0.0, w_kind=0.0)
    s = c.score([_b("x", 0)], now_step=1, goal="g")
    assert 0.0 <= s["x"] <= 1.0
