# Install LETHE in Codex

LETHE works in Codex through the same MCP server.

```bash
pip install "lethe-llm-context[mcp]"
```

Then add it to your Codex config (`~/.codex/config.toml`):

```toml
[mcp_servers.lethe]
command = "python"
args = ["-m", "lethe.mcp.server"]

# optional: choose where the archive lives
[mcp_servers.lethe.env]
LETHE_DB = "./lethe.db"
```

Restart Codex. It will discover three tools — `lethe_archive`, `lethe_recall`,
`lethe_status` — which let the agent offload large outputs out of its context and recall them
on demand, saving tokens during long tasks.

## Guiding instruction

Add the offload rule to your Codex instructions (e.g. `AGENTS.md` or your prompt) so the agent
does it automatically — see [`../claude-code/SKILL.md`](../claude-code/SKILL.md) for the exact
wording.

## Verify

Ask Codex: *"Call lethe_status."* You should get back the archived count and tokens offloaded.
