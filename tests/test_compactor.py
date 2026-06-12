from lethe.core.block import Block
from lethe.adapters.fake import FakeAdapter
from lethe.agents.compactor import Compactor


def _b(id, step, content):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)


def test_compacts_cold_run_into_one_note():
    adapter = FakeAdapter(handler=lambda msgs: "SUMMARY: did steps 1-3")
    comp = Compactor(adapter)
    run = [_b("1", 1, "x" * 100), _b("2", 2, "y" * 100), _b("3", 3, "z" * 100)]
    note = comp.compact(run, session="s")
    assert note is not None
    assert note.covers == ["1", "2", "3"]
    assert "SUMMARY" in note.summary


def test_skips_when_no_savings():
    adapter = FakeAdapter(handler=lambda msgs: "x" * 1000)  # summary bigger than originals
    comp = Compactor(adapter)
    run = [_b("1", 1, "tiny")]
    note = comp.compact(run, session="s")
    assert note is None


def test_never_compacts_pinned():
    adapter = FakeAdapter(handler=lambda msgs: "SUMMARY")
    comp = Compactor(adapter)
    pinned = _b("p", 1, "x" * 100)
    pinned.pinned = True
    note = comp.compact([pinned], session="s")
    assert note is None
