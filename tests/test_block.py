from lethe.core.block import Block, Message, BlockState


def test_block_defaults():
    b = Block(id="1", role="tool", kind="tool_result", content="hi", created_step=0)
    assert b.state is BlockState.ACTIVE
    assert b.pinned is False
    assert b.tokens is None
    assert b.refs == []
    assert b.handle is None


def test_message_holds_blocks():
    b = Block(id="1", role="user", kind="text", content="hello", created_step=0)
    m = Message(role="user", blocks=[b])
    assert m.blocks[0].content == "hello"


def test_blockstate_values():
    assert {s.value for s in BlockState} == {
        "active", "warm", "compacted", "paged", "rehydrated"
    }
