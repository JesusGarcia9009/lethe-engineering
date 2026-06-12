"""Read-only live console view of the working set. Displays state; changes nothing."""
from __future__ import annotations

from lethe.core.block import Block, BlockState


def _bar(used: int, budget: int, width: int = 18) -> str:
    frac = 0.0 if budget == 0 else min(1.0, used / budget)
    filled = int(frac * width)
    pct = int(frac * 100)
    return "#" * filled + "." * (width - filled) + f"  {pct}% de presupuesto"


def _tag(b: Block) -> str:
    if b.meta.get("stub_for"):
        return "[paged]"
    if b.pinned:
        return "PIN   "
    if b.state is BlockState.PAGED:
        return "[paged]"
    if b.kind == "note":
        return "NOTE  "
    if b.state is BlockState.WARM:
        return "WARM  "
    return "ACTIVE"


def render_frame(blocks: list[Block], goal: str, step: int,
                 used_tokens: int, budget_tokens: int, stats: dict | None = None) -> str:
    lines = [
        f'Paso {step} | Objetivo: "{goal}"',
        f"Pizarra: {_bar(used_tokens, budget_tokens)}",
        "",
    ]
    for b in blocks:
        preview = b.content.replace("\n", " ")[:48]
        lines.append(f"{_tag(b)}  paso {b.created_step:>3}  {preview}")
    if stats:
        lines += [
            "",
            (f"sin LETHE: {stats['tokens_without_lethe']} tok  |  "
             f"con LETHE: {stats['tokens_with_lethe']} tok"),
        ]
    return "\n".join(lines)
