"""See the MCP tools save tokens — no API key, no MCP host needed.

    python -m lethe.examples.mcp_demo

Simulates an agent that runs commands returning huge outputs. Without LETHE
they pile up in the context window; with LETHE each is archived to a 4-char
handle (tiny stub stays in context) and recalled losslessly on demand.

This drives the SAME logic the MCP tools `lethe_archive` / `lethe_recall` /
`lethe_status` expose — so what you see here is exactly what your agent gets.
"""
from __future__ import annotations

import os
import sys
import time

from lethe.stores.memory import MemoryStore
from lethe.mcp.service import LetheMemory, simple_tokens

# Windows consoles default to cp1252; force UTF-8 so the arrows render.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - older interpreters / odd streams
    pass

# --- tiny ANSI helpers (honor NO_COLOR / non-tty) ---------------------------
_COLOR = sys.stdout.isatty() and os.environ.get("NO_COLOR") is None


def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text


def dim(t):    return _c(t, "2")
def bold(t):   return _c(t, "1")
def green(t):  return _c(t, "32")
def cyan(t):   return _c(t, "36")
def yellow(t): return _c(t, "33")
def red(t):    return _c(t, "31")


def pause(seconds: float = 0.6) -> None:
    """Small beat so the recording feels alive; set LETHE_DEMO_FAST=1 to skip."""
    if not os.environ.get("LETHE_DEMO_FAST"):
        time.sleep(seconds)


# --- a believable agent transcript ------------------------------------------
TOOL_OUTPUTS = [
    ("build.log",   "ERROR " + ("verbose webpack build output line ... " * 90)),
    ("pytest.txt",  "collected 412 items ... " + ("PASSED test_module_xyz ... " * 70)),
    ("db_dump.json", '{"users": [' + ('{"id": 1, "email": "noise@example.com"}, ' * 80) +
                     '], "launch_code": "4242"}'),
    ("trace.txt",   "Traceback (most recent call last): " + ("  File frame ... line ... \n" * 60)),
]


def banner() -> None:
    print(bold(cyan("\n  LETHE — context garbage collector for LLM agents")))
    print(dim("  archive big tool outputs · recall on demand · save tokens\n"))


def main() -> None:
    banner()
    mem = LetheMemory(MemoryStore(), session="demo")

    without_lethe = 0   # tokens if every full output stayed in context
    with_lethe = 0      # tokens actually left in context (stubs only)
    handles = []

    print(bold("The agent runs 4 commands. Each returns a wall of text:\n"))
    pause(0.4)

    for label, content in TOOL_OUTPUTS:
        full = simple_tokens(content)
        without_lethe += full

        # >>> this is the MCP `lethe_archive` tool <<<
        r = mem.archive(content, label=label)
        with_lethe += simple_tokens(r["stub"])
        handles.append((label, r["handle"]))

        print(f"  {yellow('→ ' + label):<24} "
              f"{red(f'{full:>4} tok')} in context  "
              f"{dim('—archive→')}  "
              f"{green('stub ' + repr(r['stub']))}  "
              f"{cyan('handle=' + r['handle'])}")
        pause()

    print()
    pause(0.3)

    # >>> this is the MCP `lethe_status` tool <<<
    s = mem.status()
    print(bold("lethe_status:  ") +
          f"{s['archived']} blocks archived, "
          f"{green(str(s['tokens_offloaded']) + ' tokens')} moved out of context")
    pause()

    # >>> this is the MCP `lethe_recall` tool — lossless retrieval <<<
    print(bold("\n30 steps later the agent needs a buried fact. It recalls by keyword:\n"))
    pause(0.4)
    hit = mem.recall("launch_code")
    found = "4242" if hit and "4242" in hit else "(not found)"
    print(f"  {cyan('lethe_recall(\"launch_code\")')}  →  "
          f"found {green('launch_code = ' + found)} "
          f"{dim('(rehydrated losslessly from the archive)')}")
    pause()

    # --- the headline number -------------------------------------------------
    saved = without_lethe - with_lethe
    pct = round(100 * saved / without_lethe) if without_lethe else 0
    print(bold("\n  Context window cost\n"))
    print(f"    without LETHE : {red(f'{without_lethe:>5} tok')}  {dim('(everything stays resident)')}")
    print(f"    with LETHE    : {green(f'{with_lethe:>5} tok')}  {dim('(only tiny stubs remain)')}")
    print(bold(f"    saved         : {green(f'{saved:>5} tok')}  ({green(f'-{pct}%')})\n"))
    pause(0.4)

    print(dim("  pip install \"lethe-llm-context[mcp]\"  ·  claude mcp add lethe -- lethe-mcp\n"))


if __name__ == "__main__":
    main()
