from lethe.stores.memory import MemoryStore
from lethe.mcp.service import LetheMemory, simple_tokens


def mem():
    return LetheMemory(MemoryStore())


def test_archive_returns_handle_and_saving():
    m = mem()
    r = m.archive("x" * 4000, label="big.log")
    assert len(r["handle"]) == 8
    assert r["tokens_saved"] > 0
    assert m.recall(r["handle"]) == "x" * 4000


def test_handles_are_unique_across_many_archives():
    # C4 regression: 4-char handles collided ~50% by ~300 archives, silently
    # returning the wrong content on recall. Handles must stay distinct.
    m = mem()
    handles = {m.archive(f"content number {i}")["handle"] for i in range(500)}
    assert len(handles) == 500


def test_recall_by_keyword():
    m = mem()
    m.archive("the launch code is 4242")
    assert "4242" in m.recall("launch code")


def test_recall_unknown_returns_none():
    assert mem().recall("zzzz") is None


def test_status_counts_and_accumulates():
    m = mem()
    m.archive("a" * 400)
    m.archive("b" * 800)
    s = m.status()
    assert s["archived"] == 2
    assert s["tokens_offloaded"] == simple_tokens("a" * 400) + simple_tokens("b" * 800)


def test_simple_tokens_deterministic():
    assert simple_tokens("abcd") == 1 and simple_tokens("abcdefgh") == 2
