from lethe.core.block import Block, BlockState
from lethe.viz.console import render_frame


def _b(id, step, content, state=BlockState.ACTIVE, pinned=False, handle=None, kind="tool_result"):
    return Block(id=id, role="tool", kind=kind, content=content,
                 created_step=step, state=state, pinned=pinned, handle=handle)


def test_frame_shows_states_and_budget():
    blocks = [
        _b("g", 0, "goal", pinned=True),
        _b("a", 9, "recent"),
        _b("note", 7, "summary of steps 1-6", kind="note"),
        _b("stub-1", 5, "[paged: file @step5 · handle=a3f9]",
           state=BlockState.PAGED, handle="a3f9"),
    ]
    frame = render_frame(blocks, goal="Refactor login", step=9,
                         used_tokens=58, budget_tokens=60,
                         stats={"tokens_without_lethe": 184, "tokens_with_lethe": 58})
    assert "Refactor login" in frame
    assert "PIN" in frame
    assert "NOTE" in frame
    assert "paged" in frame
    assert "%" in frame   # budget bar percentage
