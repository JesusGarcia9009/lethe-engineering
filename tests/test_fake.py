from lethe.core.block import Block, Message
from lethe.adapters.fake import FakeAdapter, FakeTokenCounter


def _b(content, **kw):
    kw.setdefault("role", "tool")
    kw.setdefault("kind", "tool_result")
    kw.setdefault("created_step", 0)
    return Block(id=kw.pop("id", "x"), content=content, **kw)


def test_token_counter_is_deterministic():
    tc = FakeTokenCounter()
    blocks = [_b("abcd"), _b("abcdefgh")]   # 4 and 8 chars -> 1 and 2 tokens
    assert tc.count(blocks) == 3
    assert tc.count(blocks) == 3            # stable


def test_complete_returns_scripted_response():
    a = FakeAdapter(scripted=["RESULT-1", "RESULT-2"])
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "RESULT-1"
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "RESULT-2"


def test_complete_uses_handler_when_given():
    a = FakeAdapter(handler=lambda msgs: "0.9")
    assert a.complete([Message(role="user", blocks=[_b("hi")])]).text == "0.9"
