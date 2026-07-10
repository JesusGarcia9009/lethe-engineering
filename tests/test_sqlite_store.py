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


def test_refs_are_persisted_and_replaced(tmp_path):
    s = SqliteStore(str(tmp_path / "t.db"))
    b = _b("src", "cites two blocks")
    b.refs = ["a", "b"]
    s.put(b)
    assert set(s.refs_of("src")) == {"a", "b"}
    # re-putting the block replaces its edges, no duplicates
    b.refs = ["c"]
    s.put(b)
    assert s.refs_of("src") == ["c"]


def test_fts_search_with_special_chars_does_not_crash(tmp_path):
    # C5 regression: raw model keywords with FTS operators/quotes used to raise
    # sqlite3.OperationalError and take down lethe_recall. They must be safe now.
    s = SqliteStore(str(tmp_path / "t.db"))
    s.put(_b("1", "auth JWT flow tokens", handle="h1"))
    for q in ['auth: JWT', 'flow"broken', 'tokens AND (', '*', 'NEAR foo', '']:
        s.search(q, limit=5)   # must not raise
    assert "1" in {h.id for h in s.search("JWT", limit=5)}
