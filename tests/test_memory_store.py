from lethe.core.block import Block
from lethe.stores.memory import MemoryStore


def _b(id, content, handle=None):
    return Block(id=id, role="tool", kind="tool_result", content=content,
                 created_step=0, handle=handle)


def test_put_and_get_by_handle():
    s = MemoryStore()
    s.put(_b("1", "config contents", handle="a3f9"))
    got = s.get("a3f9")
    assert got is not None and got.content == "config contents"


def test_lexical_search_finds_keyword():
    s = MemoryStore()
    s.put(_b("1", "the secret needle is 4242", handle="h1"))
    s.put(_b("2", "unrelated log line", handle="h2"))
    hits = s.search("needle", limit=5)
    assert [h.id for h in hits] == ["1"]


def test_events_are_recorded():
    s = MemoryStore()
    s.events("page_out", {"handle": "h1"})
    assert s.event_log[-1]["kind"] == "page_out"
