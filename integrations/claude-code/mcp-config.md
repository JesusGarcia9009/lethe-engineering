# Install LETHE in Claude Code

LETHE plugs into Claude Code as an MCP server. Two lines:

```bash
pip install "lethe[mcp]"
claude mcp add lethe -- python -m lethe.mcp.server
```

That registers a local stdio MCP server exposing three tools:

| Tool | What it does |
|---|---|
| `lethe_archive(content, label)` | Store a big output out of context; returns a short handle |
| `lethe_recall(query_or_handle)` | Get archived content back by handle or keyword |
| `lethe_status()` | See how many tokens you've offloaded |

## Make it automatic (recommended)

Copy the guiding skill so Claude offloads large outputs on its own:

```bash
mkdir -p ~/.claude/skills/lethe-offload
cp integrations/claude-code/SKILL.md ~/.claude/skills/lethe-offload/SKILL.md
```

Now, during long tasks, Claude will archive verbose outputs to LETHE and recall them when
needed — keeping its context window small and saving you tokens.

## Configuration

- `LETHE_DB` env var sets the SQLite path (default `./lethe.db`).

## Verify it works

In a Claude Code session, ask: *"Call lethe_status."* You should get back the archived count
and tokens offloaded.
