from lethe.core.block import Block
from lethe.stores.sqlite import SqliteStore


def _b(id, content, handle=None, step=0):
    return Block(id=id, role="tool", kind="tool_result", content=content,
                 created_step=step, handle=handle)


def test_roundtrip_by_handle(tmp_path):
    s = SqliteStore(str(tmp_path / "t.db"))
    s.put(_b("1", "config contents", handle="a3f9"))
    got = s.get("a3f9")
    assert got is not None and got.content == "config contents"


def test_fts_search(tmp_path):
    s = SqliteStore(str(tmp_path / "t.db"))
    s.put(_b("1", "the secret needle is 4242", handle="h1"))
    s.put(_b("2", "unrelated log line", handle="h2"))
    hits = s.search("needle", limit=5)
    assert "1" in {h.id for h in hits}
