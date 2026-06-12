from lethe.core.block import Block, BlockState
from lethe.stores.memory import MemoryStore
from lethe.agents.archivist import Archivist, make_handle


def _b(id, content, step=0):
    return Block(id=id, role="tool", kind="tool_result", content=content, created_step=step)


def test_page_out_sets_handle_state_and_stub():
    store = MemoryStore()
    arch = Archivist(store)
    b = _b("1", "big config file contents", step=5)
    stub = arch.page_out(b)
    assert b.state is BlockState.PAGED
    assert b.handle is not None
    assert "paged" in stub.content and b.handle in stub.content
    assert store.get(b.handle).content == "big config file contents"


def test_page_fault_by_handle_restores():
    store = MemoryStore()
    arch = Archivist(store)
    b = _b("1", "secret needle 4242", step=5)
    arch.page_out(b)
    got = arch.page_fault(b.handle)
    assert got is not None and got.content == "secret needle 4242"
    assert got.state is BlockState.REHYDRATED


def test_recall_lexical_finds_block():
    store = MemoryStore()
    arch = Archivist(store)
    arch.page_out(_b("1", "the needle is 4242", step=1))
    hits = arch.recall("needle")
    assert hits and hits[0].content == "the needle is 4242"
